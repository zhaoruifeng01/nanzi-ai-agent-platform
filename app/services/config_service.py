import asyncio
import logging
import os
import time
from typing import Optional, Dict, List, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.orm import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_PREFIX = "sys_config:"
CACHE_TTL = 300  # 5 minutes

class ConfigService:
    
    # Memory Cache for get_all_from_db
    _all_configs_cache: Optional[Dict[str, dict]] = None
    _all_configs_last_fetched: float = 0
    _ALL_CONFIGS_TTL = 60.0  # 60 seconds
    _all_configs_load_lock = asyncio.Lock()

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._all_configs_cache = None
        cls._all_configs_last_fetched = 0

    @classmethod
    def _all_configs_cache_is_fresh(cls) -> bool:
        return (
            cls._all_configs_cache is not None
            and time.time() - cls._all_configs_last_fetched < cls._ALL_CONFIGS_TTL
        )

    @classmethod
    async def _fetch_all_configs(cls, session: AsyncSession) -> Dict[str, dict]:
        result = await session.execute(
            text(
                "SELECT `key`, `value`, `description`, `category`, `is_secret` "
                "FROM system_configs"
            )
        )
        return {
            row[0]: {
                "value": row[1],
                "description": row[2],
                "category": row[3],
                "is_secret": bool(row[4]),
            }
            for row in result.fetchall()
        }

    @classmethod
    async def get_all_from_db(
        cls,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, dict]:
        """
        Retrieves all configs from DB.
        Returns a dict: { key: { value, description, category, is_secret } }
        Now uses short-term memory cache (60s).
        """
        if cls._all_configs_cache_is_fresh():
            return cls._all_configs_cache or {}

        async with cls._all_configs_load_lock:
            if cls._all_configs_cache_is_fresh():
                return cls._all_configs_cache or {}

            if db is not None:
                configs = await cls._fetch_all_configs(db)
            else:
                async with AsyncSessionLocal() as session:
                    configs = await cls._fetch_all_configs(session)

            cls._all_configs_cache = configs
            cls._all_configs_last_fetched = time.time()
            return configs

    @staticmethod
    async def get(
        key: str,
        default: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[str]:
        """
        Get configuration value.
        Load the complete configuration table once per process cache window,
        then resolve individual keys from the in-memory snapshot.
        """
        try:
            configs = await ConfigService.get_all_from_db(db=db)
        except Exception as e:
            logger.error(f"Failed to fetch config '{key}' from DB: {e}")
            return default

        config = configs.get(key)
        if config:
            value = config.get("value")
            if value is not None and value != "":
                return value
        return default

    @staticmethod
    async def set_config(
        key: str, 
        value: str, 
        description: Optional[str] = None, 
        category: str = "general", 
        is_secret: bool = False,
        changed_by: str = "system",
        change_reason: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Set configuration value in DB and update Redis.
        Now supports Audit Logging.
        """
        from app.services.auth_service import AuthService
        session, is_local = await AuthService._get_session(db)
        try:
            # 1. Fetch old value for audit
            result = await session.execute(
                text("SELECT value FROM system_configs WHERE `key` = :key"), 
                {"key": key}
            )
            row = result.fetchone()
            old_value = row[0] if row else None
            change_type = "UPDATE" if row else "CREATE"

            # 2. Upsert config
            # Note: ON DUPLICATE KEY UPDATE is specific to MySQL
            sql = """
                INSERT INTO system_configs (`key`, `value`, `description`, `category`, `is_secret`)
                VALUES (:key, :value, :description, :category, :is_secret)
                ON DUPLICATE KEY UPDATE
                    `value` = VALUES(`value`),
                    `description` = COALESCE(VALUES(`description`), system_configs.`description`),
                    `category` = COALESCE(VALUES(`category`), system_configs.`category`),
                    `is_secret` = COALESCE(VALUES(`is_secret`), system_configs.`is_secret`)
            """
            await session.execute(text(sql), {
                "key": key, 
                "value": value, 
                "description": description, 
                "category": category, 
                "is_secret": is_secret
            })
            
            # 3. Insert Audit Log
            # Only log if value changed or it's a new key
            if old_value != value:
                audit_sql = """
                    INSERT INTO system_config_history 
                    (config_key, old_value, new_value, description, changed_by, change_type)
                    VALUES (:key, :old_value, :new_value, :audit_desc, :changed_by, :change_type)
                """
                # Use provided change_reason if available, else description, else generic
                audit_desc = change_reason or description or "Config updated via set_config"
                
                await session.execute(text(audit_sql), {
                    "key": key, 
                    "old_value": old_value, 
                    "new_value": value, 
                    "audit_desc": audit_desc, 
                    "changed_by": changed_by, 
                    "change_type": change_type
                })
            
            await session.commit()
            
        except Exception:
            await session.rollback()
            raise
        finally:
            if is_local:
                await session.close()
        
        redis = await get_redis()
        if redis:
            await redis.set(f"{CACHE_PREFIX}{key}", value, ex=CACHE_TTL)
            logger.info(f"Config '{key}' updated in DB and Redis. Audit log created.")
        
        # Invalidate Memory Cache
        ConfigService.invalidate_cache()
            
        return old_value != value

    @staticmethod
    async def set_configs_batch(
        items: List[Dict[str, Any]],
        *,
        changed_by: str = "system",
        db: Optional[AsyncSession] = None,
    ) -> None:
        """
        批量写入多个配置项:单事务 + 单 commit + 单次缓存失效。
        适合一次保存多字段的场景(如品牌设置 9 个字段),把 N×(SELECT+upsert+history+commit)
        收敛为常数次 round-trip,在跨地域远程 DB 上从 ~16s 降到 ~2-3s。

        items: [{"key","value","description","category","is_secret","change_reason"}, ...]
        """
        if not items:
            return
        from sqlalchemy import bindparam
        from app.services.auth_service import AuthService

        session, is_local = await AuthService._get_session(db)
        try:
            keys = [it["key"] for it in items]

            # 1. 一次取出所有旧值(判断是否变化 + 审计 old_value)
            result = await session.execute(
                text(
                    "SELECT `key`, `value` FROM system_configs WHERE `key` IN :keys"
                ).bindparams(bindparam("keys", expanding=True)),
                {"keys": keys},
            )
            old_values = {row[0]: row[1] for row in result.fetchall()}

            # 2. 批量 upsert(多行 VALUES + ON DUPLICATE KEY UPDATE)
            value_ph: List[str] = []
            params: Dict[str, Any] = {}
            for i, it in enumerate(items):
                value_ph.append(f"(:k{i}, :v{i}, :d{i}, :c{i}, :s{i})")
                params[f"k{i}"] = it["key"]
                params[f"v{i}"] = it["value"]
                params[f"d{i}"] = it.get("description")
                params[f"c{i}"] = it.get("category", "general")
                params[f"s{i}"] = bool(it.get("is_secret", False))
            upsert_sql = (
                "INSERT INTO system_configs "
                "(`key`, `value`, `description`, `category`, `is_secret`) "
                "VALUES " + ", ".join(value_ph) + " "
                "ON DUPLICATE KEY UPDATE "
                "`value` = VALUES(`value`), "
                "`description` = COALESCE(VALUES(`description`), system_configs.`description`), "
                "`category` = COALESCE(VALUES(`category`), system_configs.`category`), "
                "`is_secret` = COALESCE(VALUES(`is_secret`), system_configs.`is_secret`)"
            )
            await session.execute(text(upsert_sql), params)

            # 3. 批量写审计历史(仅记录值变化的项)
            hist_ph: List[str] = []
            hist_params: Dict[str, Any] = {}
            h = 0
            for it in items:
                key = it["key"]
                old = old_values.get(key)
                new = it["value"]
                if old == new:
                    continue
                hist_ph.append(f"(:hk{h}, :ho{h}, :hn{h}, :hd{h}, :hb{h}, :ht{h})")
                hist_params[f"hk{h}"] = key
                hist_params[f"ho{h}"] = old
                hist_params[f"hn{h}"] = new
                hist_params[f"hd{h}"] = (
                    it.get("change_reason")
                    or it.get("description")
                    or "Config updated via set_configs_batch"
                )
                hist_params[f"hb{h}"] = changed_by
                hist_params[f"ht{h}"] = "UPDATE" if old is not None else "CREATE"
                h += 1
            if hist_ph:
                hist_sql = (
                    "INSERT INTO system_config_history "
                    "(config_key, old_value, new_value, description, changed_by, change_type) "
                    "VALUES " + ", ".join(hist_ph)
                )
                await session.execute(text(hist_sql), hist_params)

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            if is_local:
                await session.close()

        # 4. Redis 批量刷新(pipeline)
        redis = await get_redis()
        if redis:
            try:
                pipe = redis.pipeline()
                for it in items:
                    pipe.set(f"{CACHE_PREFIX}{it['key']}", it["value"], ex=CACHE_TTL)
                await pipe.execute()
            except Exception as e:
                logger.warning(f"Failed to refresh Redis for batch configs: {e}")

        # 5. 单次内存缓存失效
        ConfigService.invalidate_cache()
        logger.info(f"Batch updated {len(items)} configs in a single transaction.")

    @staticmethod
    async def get_all_configs_grouped() -> Dict[str, List[dict]]:
        """
        Get all configs grouped by category for UI display.
        Secrets are masked.
        """
        configs = await ConfigService.get_all_from_db()
        grouped = {}
        
        for key, data in configs.items():
            cat = data['category']
            if cat == 'branding':
                continue
            if cat not in grouped:
                grouped[cat] = []
            
            # Mask secret
            display_value = data['value']
            if data['is_secret'] and display_value:
                if len(display_value) > 8:
                    display_value = display_value[:3] + "****" + display_value[-4:]
                else:
                    display_value = "****"
            
            grouped[cat].append({
                "key": key,
                "value": display_value, # Masked for display
                "description": data['description'],
                "is_secret": data['is_secret']
            })
            
        return grouped

    @staticmethod
    async def update_config_value(key: str, value: str, changed_by: str = "system", change_reason: Optional[str] = None) -> bool:
        """
        Update ONLY the configuration value in DB and Redis.
        Preserves other fields (category, description, is_secret).
        """
        old_value = None # Initialize old_value outside the session block
        async with AsyncSessionLocal() as session:
            try:
                # 1. Fetch old value
                result = await session.execute(
                    text("SELECT value FROM system_configs WHERE `key` = :key"), 
                    {"key": key}
                )
                row = result.fetchone()
                old_value = row[0] if row else None
                
                if old_value is None:
                    # Key doesn't exist, we must use set_config but since we are in async context manager here,
                    # we should probably close, or just handle logic here.
                    # Simpler is to return and let caller handle, or recursive call?
                    # Since we're inside a session, calling set_config (which creates new session) is safe but inefficient.
                    # Ideally we replicate logic. But for now, let's just use recursive call after exiting session?
                    pass 
                
                # Logic if exists:
                if old_value is not None:
                    # 2. Update value
                    await session.execute(
                        text("UPDATE system_configs SET value = :value WHERE `key` = :key"),
                        {"value": value, "key": key}
                    )
                    
                    # 3. Audit Log
                    if old_value != value:
                        audit_sql = """
                            INSERT INTO system_config_history 
                            (config_key, old_value, new_value, description, changed_by, change_type)
                            VALUES (:key, :old_value, :value, :audit_desc, :changed_by, 'UPDATE')
                        """
                        audit_desc = change_reason or "Value updated"
                        await session.execute(text(audit_sql), {
                            "key": key, 
                            "old_value": old_value, 
                            "value": value, 
                            "audit_desc": audit_desc, 
                            "changed_by": changed_by
                        })
                    
                    await session.commit()
            except Exception:
                await session.rollback()
                raise

        if old_value is None:
             # Fallback to set_config outside of the session block
             return await ConfigService.set_config(key, value, changed_by=changed_by, change_reason=change_reason)
        
        redis = await get_redis()
        if redis:
            await redis.set(f"{CACHE_PREFIX}{key}", value, ex=CACHE_TTL)
            logger.info(f"Config '{key}' value updated. Audit log created.")
        
        # Invalidate Memory Cache
        ConfigService.invalidate_cache()
            
        return old_value != value

    @staticmethod
    async def bulk_update(updates: List[dict], changed_by: str = "system"):
        """
        Bulk update configs.
        updates: [{key, value}, ...]
        """
        for item in updates:
            key = item.get('key')
            val = item.get('value')
            if key is not None and val is not None:
                await ConfigService.update_config_value(key, val, changed_by=changed_by, change_reason="Bulk update")

    @staticmethod
    async def get_config_history(key: str, limit: int = 50) -> List[dict]:
        """
        Get history of a specific configuration key.
        """
        async with AsyncSessionLocal() as session:
            sql = """
                SELECT id, config_key, old_value, new_value, description, changed_by, change_type, created_at
                FROM system_config_history
                WHERE config_key = :key
                ORDER BY created_at DESC
                LIMIT :limit
            """
            result = await session.execute(text(sql), {"key": key, "limit": limit})
            rows = result.fetchall()
            
            history = []
            for r in rows:
                history.append({
                    "id": r[0],
                    "config_key": r[1],
                    "old_value": r[2],
                    "new_value": r[3],
                    "description": r[4],
                    "changed_by": r[5],
                    "change_type": r[6],
                    "created_at": r[7].strftime("%Y-%m-%d %H:%M:%S") if r[7] else ""
                })
            return history
