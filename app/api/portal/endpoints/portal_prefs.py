"""
数据门户个人偏好接口（Portal Preferences）

存储用户置顶的数据门户卡片 ID 列表到 Redis。
Key: agent:portal_prefs:{user_id}
Value: JSON 字符串，结构为 { "pinned_group_ids": ["id1", "id2"] }
"""
import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import require_api_key
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PINNED_GROUPS = 50  # 最多允许置顶的卡片数，防止滥用


def _redis_key(user_id: int) -> str:
    return f"agent:portal_prefs:{user_id}"


class PortalPrefs(BaseModel):
    pinned_group_ids: List[str] = Field(default_factory=list, description="已置顶的数据门户卡片 ID 列表，保持插入顺序")


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="获取当前用户的数据门户偏好设置",
)
async def get_portal_prefs(
    user_info: Dict[str, Any] = Depends(require_api_key),
):
    redis = await get_redis()
    if not redis:
        return {"code": 0, "data": PortalPrefs().model_dump()}

    user_id = int(user_info["user_id"])
    key = _redis_key(user_id)
    try:
        raw = await redis.get(key)
    except Exception as e:
        logger.error("Failed to get portal prefs from Redis: %s", e)
        return {"code": 0, "data": PortalPrefs().model_dump()}

    if not raw:
        return {"code": 0, "data": PortalPrefs().model_dump()}

    try:
        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        parsed = json.loads(decoded)
        prefs = PortalPrefs.model_validate(parsed)
    except Exception as e:
        logger.warning("Failed to parse portal prefs JSON: %s", e)
        prefs = PortalPrefs()

    return {"code": 0, "data": prefs.model_dump()}


@router.put(
    "",
    response_model=Dict[str, Any],
    summary="保存当前用户的数据门户偏好设置",
)
async def update_portal_prefs(
    body: PortalPrefs,
    user_info: Dict[str, Any] = Depends(require_api_key),
):
    redis = await get_redis()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 服务不可用",
        )

    user_id = int(user_info["user_id"])
    key = _redis_key(user_id)

    # 去重并限制最大数量
    seen = set()
    deduped: List[str] = []
    for gid in body.pinned_group_ids:
        gid = gid.strip()
        if gid and gid not in seen:
            seen.add(gid)
            deduped.append(gid)
            if len(deduped) >= MAX_PINNED_GROUPS:
                break

    prefs = PortalPrefs(pinned_group_ids=deduped)

    try:
        # 不设置 TTL，长期保留用户偏好
        await redis.set(key, prefs.model_dump_json())
    except Exception as e:
        logger.error("Failed to save portal prefs to Redis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存偏好设置失败",
        )

    return {"code": 0, "data": prefs.model_dump(), "message": "偏好已保存"}
