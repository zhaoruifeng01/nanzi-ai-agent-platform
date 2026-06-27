import json
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_api_key
from app.core.orm import get_db_session
from app.core.redis import get_redis
from app.schemas.response import StandardResponse
from app.services.sql_query_execution_service import execute_sql_query_core

logger = logging.getLogger(__name__)

router = APIRouter()

class SaveReportRequest(BaseModel):
    title: str = Field(..., description="报表自定义标题")
    sql_content: str = Field(..., description="只读 SELECT 语句")
    dataset_id: Optional[int] = Field(None, description="数据集 ID")
    data_source: str = Field(..., description="数据源标识，如 default_clickhouse、mysql_oa")
    original_query: Optional[str] = Field(None, description="原始提问语句")
    mode: str = Field("static_sql", description="报表模式：static_sql 或 param_sql")
    sql_template: Optional[str] = Field(None, description="参数化 SQL 模板")
    params_schema: List[Dict[str, Any]] = Field(default_factory=list, description="运行参数定义")
    default_params: Dict[str, Any] = Field(default_factory=dict, description="默认运行参数")
    analysis_mode: str = Field("manual", description="执行后分析模式：manual 或 auto")


class ExecuteReportRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict, description="本次运行参数")
    analysis_mode: Optional[str] = Field(None, description="覆盖报表默认分析模式")


class UpdateReportRequest(BaseModel):
    title: Optional[str] = Field(None, description="报表自定义标题")
    sql_content: Optional[str] = Field(None, description="只读 SELECT 语句")
    dataset_id: Optional[int] = Field(None, description="数据集 ID")
    data_source: Optional[str] = Field(None, description="数据源标识，如 default_clickhouse、mysql_oa")
    original_query: Optional[str] = Field(None, description="原始提问语句")
    mode: Optional[str] = Field(None, description="报表模式：static_sql 或 param_sql")
    sql_template: Optional[str] = Field(None, description="参数化 SQL 模板")
    params_schema: Optional[List[Dict[str, Any]]] = Field(None, description="运行参数定义")
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认运行参数")
    analysis_mode: Optional[str] = Field(None, description="执行后分析模式：manual 或 auto")


class SavedReportItem(BaseModel):
    id: str
    title: str
    sql_content: str
    dataset_id: Optional[int]
    data_source: str
    original_query: Optional[str]
    created_at: str
    mode: str = "static_sql"
    sql_template: Optional[str] = None
    params_schema: List[Dict[str, Any]] = Field(default_factory=list)
    default_params: Dict[str, Any] = Field(default_factory=dict)
    analysis_mode: str = "manual"


class ReportParameterError(ValueError):
    pass


_SQL_GATE_ERROR_PREFIXES = ("[Validation Failed]", "[Permission Denied]", "[Security Error]")


def _redis_key(user_id: int) -> str:
    return f"agent:saved_reports:{user_id}"

def _chatbi_user_dimensions(user_info: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    return {
        "id": user_id,
        "user_name": user_info.get("user_name"),
        "real_name": user_info.get("real_name"),
        "role": user_info.get("role"),
        "dept_code": user_info.get("dept_code"),
        "org_path": user_info.get("org_path"),
        "extra_data": user_info.get("extra_data"),
    }


def _detect_default_date_range_template(sql: str) -> Tuple[Optional[str], List[Dict[str, Any]], Dict[str, Any]]:
    matches = list(re.finditer(r"'(\d{4}-\d{2}-\d{2})'", sql))
    if len(matches) < 2:
        return None, [], {}

    first, second = matches[0], matches[1]
    template = f"{sql[:first.start()]}{{{{start_date}}}}{sql[first.end():second.start()]}{{{{end_date}}}}{sql[second.end():]}"
    params_schema = [
        {
            "name": "date_range",
            "type": "date_range",
            "label": "日期范围",
            "default": "month_start_to_today",
            "options": ["today", "yesterday", "last_7_days", "month_start_to_today", "custom_range"],
        }
    ]
    return template, params_schema, {"date_range": "month_start_to_today"}


def _build_saved_report_item(
    *,
    report_id: str,
    title: str,
    sql_clean: str,
    dataset_id: Optional[int],
    data_source: str,
    original_query: Optional[str],
    created_at: str,
    body: SaveReportRequest,
) -> SavedReportItem:
    mode = body.mode if body.mode in {"static_sql", "param_sql"} else "static_sql"
    sql_template = body.sql_template
    params_schema = list(body.params_schema or [])
    default_params = dict(body.default_params or {})

    if not sql_template and not params_schema:
        detected_template, detected_schema, detected_defaults = _detect_default_date_range_template(sql_clean)
        if detected_template:
            mode = "param_sql"
            sql_template = detected_template
            params_schema = detected_schema
            default_params = detected_defaults

    if sql_template or params_schema:
        mode = "param_sql"

    analysis_mode = body.analysis_mode if body.analysis_mode in {"manual", "auto"} else "manual"

    return SavedReportItem(
        id=report_id,
        title=title,
        sql_content=sql_clean,
        dataset_id=dataset_id,
        data_source=data_source,
        original_query=original_query,
        created_at=created_at,
        mode=mode,
        sql_template=sql_template,
        params_schema=params_schema,
        default_params=default_params,
        analysis_mode=analysis_mode,
    )


def _decode_saved_report(raw_val: Any) -> SavedReportItem:
    decoded = raw_val.decode("utf-8") if isinstance(raw_val, bytes) else str(raw_val)
    return SavedReportItem.model_validate(json.loads(decoded))


def _parse_iso_date_param(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ReportParameterError(f"参数 {name} 必须是 YYYY-MM-DD 日期")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ReportParameterError(f"参数 {name} 必须是 YYYY-MM-DD 日期") from exc


def _resolve_builtin_date_range(params: Dict[str, Any], today: date) -> Dict[str, str]:
    date_range = str(params.get("date_range") or "month_start_to_today")
    if date_range == "today":
        start = today
        end = today + timedelta(days=1)
    elif date_range == "yesterday":
        start = today - timedelta(days=1)
        end = today
    elif date_range == "last_7_days":
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)
    elif date_range == "month_start_to_today":
        start = today.replace(day=1)
        end = today + timedelta(days=1)
    elif date_range == "custom_range":
        start = _parse_iso_date_param(params.get("start_date"), "start_date")
        end = _parse_iso_date_param(params.get("end_date"), "end_date")
        if end <= start:
            raise ReportParameterError("结束日期必须晚于开始日期")
    else:
        raise ReportParameterError("不支持的日期范围")

    return {
        "date_range": date_range,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def _allowed_template_params(report: SavedReportItem) -> set[str]:
    allowed = set()
    for item in report.params_schema:
        name = str(item.get("name") or "").strip()
        param_type = str(item.get("type") or "").strip()
        if name:
            allowed.add(name)
        if param_type == "date_range" or name == "date_range":
            allowed.update({"date_range", "start_date", "end_date"})
    return allowed


def _resolve_report_sql(
    report: SavedReportItem,
    *,
    body: ExecuteReportRequest,
    today: Optional[date] = None,
) -> Tuple[str, Dict[str, Any]]:
    if report.mode != "param_sql":
        return report.sql_content, {}

    template = report.sql_template or report.sql_content
    allowed = _allowed_template_params(report)
    placeholders = set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", template))
    unknown = placeholders - allowed
    if unknown:
        raise ReportParameterError(f"不允许的报表参数: {', '.join(sorted(unknown))}")

    merged_params = dict(report.default_params or {})
    merged_params.update(body.params or {})

    resolved_params: Dict[str, Any] = {}
    if {"start_date", "end_date"} & placeholders or merged_params.get("date_range"):
        resolved_params.update(_resolve_builtin_date_range(merged_params, today or date.today()))
    for key, value in merged_params.items():
        if key not in resolved_params:
            resolved_params[key] = value

    def replace_placeholder(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name in {"start_date", "end_date"}:
            return f"'{resolved_params[name]}'"
        raise ReportParameterError(f"参数 {name} 暂不支持直接写入 SQL 模板")

    return re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", replace_placeholder, template), resolved_params


async def _precheck_saved_report_sql_permissions(
    db: AsyncSession,
    *,
    report: SavedReportItem,
    user_info: Dict[str, Any],
    user_id: int,
) -> None:
    try:
        sql_to_check, _ = _resolve_report_sql(
            report,
            body=ExecuteReportRequest(params=report.default_params or {}),
        )
    except ReportParameterError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    try:
        result_str = await execute_sql_query_core(
            db,
            sql=sql_to_check,
            data_source=report.data_source,
            dataset_name=None,
            user_id=user_id,
            user_dimensions=_chatbi_user_dimensions(user_info, user_id),
            trace_logs=None,
            api_key=None,
            agent_context=None,
            dry_run=False,
            auth_check_only=True,
            is_admin=user_info.get("role") == "admin",
            bypass_table_auth=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to precheck saved report SQL permissions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报表 SQL 权限校验失败: {e}",
        ) from e

    raw_res = str(result_str or "").strip()
    if raw_res.startswith(_SQL_GATE_ERROR_PREFIXES):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=raw_res)

    try:
        parsed = json.loads(raw_res)
    except json.JSONDecodeError:
        return

    if isinstance(parsed, dict) and parsed.get("allowed") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=parsed)

@router.post(
    "",
    response_model=StandardResponse[SavedReportItem],
    summary="暂存黄金 SQL 报表到数据门户",
)
async def save_report(
    body: SaveReportRequest,
    user_info: Dict[str, Any] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    redis = await get_redis()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 服务不可用",
        )

    user_id = int(user_info["user_id"])

    # 自动推导并补全 dataset_id 和 data_source
    if not body.dataset_id:
        words = set(re.findall(r"\b[a-zA-Z0-9_]+\b", body.sql_content.lower()))
        if words:
            from sqlalchemy import select
            from app.models.metadata import MetaTable, MetaDataset
            try:
                stmt = (
                    select(MetaTable.dataset_id, MetaDataset.data_source)
                    .join(MetaDataset, MetaTable.dataset_id == MetaDataset.id)
                    .where(MetaTable.physical_name.in_(words))
                    .where(MetaTable.status == 1)
                    .limit(1)
                )
                res = await db.execute(stmt)
                row = res.first()
                if row:
                    body.dataset_id = row[0]
                    body.data_source = row[1]
            except Exception as ex:
                logger.warning("Failed to auto-detect dataset for saved report: %s", ex)

    if not body.data_source:
        body.data_source = "default_clickhouse"

    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    now_str = datetime.now(timezone.utc).isoformat()

    sql_clean = body.sql_content.strip()
    if sql_clean.startswith("[Executed SQL]:"):
        sql_clean = sql_clean[len("[Executed SQL]:"):].strip()

    report_item = _build_saved_report_item(
        report_id=report_id,
        title=body.title.strip(),
        sql_clean=sql_clean,
        dataset_id=body.dataset_id,
        data_source=body.data_source,
        original_query=body.original_query,
        created_at=now_str,
        body=body,
    )

    key = _redis_key(user_id)
    try:
        await redis.hset(key, report_id, report_item.model_dump_json())
    except Exception as e:
        logger.error("Failed to save report to Redis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存报表失败",
        )

    return StandardResponse(data=report_item)

@router.get(
    "",
    response_model=StandardResponse[List[SavedReportItem]],
    summary="获取当前用户的黄金 SQL 报表暂存列表",
)
async def get_saved_reports(
    user_info: Dict[str, Any] = Depends(require_api_key),
):
    redis = await get_redis()
    if not redis:
        return StandardResponse(data=[])

    user_id = int(user_info["user_id"])
    key = _redis_key(user_id)
    try:
        raw_reports = await redis.hgetall(key)
    except Exception as e:
        logger.error("Failed to get reports from Redis: %s", e)
        return StandardResponse(data=[])

    reports = []
    if isinstance(raw_reports, dict):
        for val in raw_reports.values():
            try:
                decoded = val.decode("utf-8") if isinstance(val, bytes) else str(val)
                parsed = json.loads(decoded)
                reports.append(SavedReportItem.model_validate(parsed))
            except Exception as e:
                logger.warning("Failed to parse saved report item JSON: %s", e)
                continue

    # 按照创建时间降序排序 (最新暂存的在最上面)
    reports.sort(key=lambda x: x.created_at, reverse=True)
    return StandardResponse(data=reports)

@router.delete(
    "/{report_id}",
    response_model=StandardResponse[Dict[str, bool]],
    summary="删除暂存的黄金 SQL 报表",
)
async def delete_saved_report(
    report_id: str,
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
    try:
        deleted_count = await redis.hdel(key, report_id)
    except Exception as e:
        logger.error("Failed to delete report from Redis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除报表失败",
        )

    if not deleted_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报表不存在或已被删除",
        )

    return StandardResponse(data={"deleted": True})


@router.put(
    "/{report_id}",
    response_model=StandardResponse[SavedReportItem],
    summary="编辑暂存的黄金 SQL 报表",
)
async def update_saved_report(
    report_id: str,
    body: UpdateReportRequest,
    user_info: Dict[str, Any] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    redis = await get_redis()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 服务不可用",
        )

    user_id = int(user_info["user_id"])
    key = _redis_key(user_id)
    try:
        raw_val = await redis.hget(key, report_id)
    except Exception as e:
        logger.error("Failed to get report detail before update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取报表详情失败",
        )

    if not raw_val:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报表不存在或无权访问",
        )

    try:
        existing = _decode_saved_report(raw_val)
    except Exception as e:
        logger.error("Failed to parse report model before update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="报表数据解析失败",
        )

    fields_set = body.model_fields_set
    sql_clean = (body.sql_content if "sql_content" in fields_set and body.sql_content is not None else existing.sql_content).strip()
    if sql_clean.startswith("[Executed SQL]:"):
        sql_clean = sql_clean[len("[Executed SQL]:"):].strip()

    title = (body.title if "title" in fields_set and body.title is not None else existing.title).strip()
    data_source = body.data_source if "data_source" in fields_set and body.data_source is not None else existing.data_source
    dataset_id = body.dataset_id if "dataset_id" in fields_set else existing.dataset_id
    original_query = body.original_query if "original_query" in fields_set else existing.original_query

    mode = body.mode if "mode" in fields_set and body.mode is not None else existing.mode
    sql_template = body.sql_template if "sql_template" in fields_set else existing.sql_template
    params_schema = body.params_schema if "params_schema" in fields_set and body.params_schema is not None else existing.params_schema
    default_params = body.default_params if "default_params" in fields_set and body.default_params is not None else existing.default_params
    analysis_mode = body.analysis_mode if "analysis_mode" in fields_set and body.analysis_mode is not None else existing.analysis_mode

    if "sql_content" in fields_set and "sql_template" not in fields_set and "params_schema" not in fields_set:
        detected_template, detected_schema, detected_defaults = _detect_default_date_range_template(sql_clean)
        if detected_template:
            mode = "param_sql"
            sql_template = detected_template
            params_schema = detected_schema
            default_params = detected_defaults
        else:
            mode = "static_sql" if "mode" not in fields_set else mode
            sql_template = None if "sql_template" not in fields_set else sql_template
            params_schema = [] if "params_schema" not in fields_set else (params_schema or [])
            default_params = {} if "default_params" not in fields_set else (default_params or {})

    update_body = SaveReportRequest(
        title=title,
        sql_content=sql_clean,
        dataset_id=dataset_id,
        data_source=data_source or "default_clickhouse",
        original_query=original_query,
        mode=mode or "static_sql",
        sql_template=sql_template,
        params_schema=params_schema or [],
        default_params=default_params or {},
        analysis_mode=analysis_mode or "manual",
    )
    report_item = _build_saved_report_item(
        report_id=existing.id,
        title=title,
        sql_clean=sql_clean,
        dataset_id=dataset_id,
        data_source=data_source or "default_clickhouse",
        original_query=original_query,
        created_at=existing.created_at,
        body=update_body,
    )

    await _precheck_saved_report_sql_permissions(
        db,
        report=report_item,
        user_info=user_info,
        user_id=user_id,
    )

    try:
        await redis.hset(key, report_id, report_item.model_dump_json())
    except Exception as e:
        logger.error("Failed to update report in Redis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新报表失败",
        )

    return StandardResponse(data=report_item)

@router.post(
    "/{report_id}/execute",
    response_model=StandardResponse[Any],
    summary="免模型极速安全运行暂存的黄金 SQL 报表",
)
async def execute_saved_report(
    report_id: str,
    body: Optional[ExecuteReportRequest] = None,
    conversation_id: Optional[str] = None, # 接收 conversation_id 以便写入缓存复用
    user_info: Dict[str, Any] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    redis = await get_redis()
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 服务不可用",
        )

    user_id = int(user_info["user_id"])
    key = _redis_key(user_id)
    try:
        raw_val = await redis.hget(key, report_id)
    except Exception as e:
        logger.error("Failed to get report detail from Redis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取报表详情失败",
        )

    if not raw_val:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报表不存在或无权访问",
        )

    try:
        report = _decode_saved_report(raw_val)
    except Exception as e:
        logger.error("Failed to parse report model: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="报表数据解析失败",
        )

    user_dimensions = _chatbi_user_dimensions(user_info, user_id)
    is_admin = user_info.get("role") == "admin"
    request_body = body or ExecuteReportRequest()

    try:
        sql_to_execute, resolved_params = _resolve_report_sql(report, body=request_body)
    except ReportParameterError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    try:
        # 参数化报表会在执行前重新经过底层 SQL 校验、沙箱与表权限校验。
        result_str = await execute_sql_query_core(
            db,
            sql=sql_to_execute,
            data_source=report.data_source,
            dataset_name=None,
            user_id=user_id,
            user_dimensions=user_dimensions,
            trace_logs=None,
            api_key=None,
            agent_context=None,
            dry_run=False,
            is_admin=is_admin,
            bypass_table_auth=False,
        )
    except Exception as e:
        logger.error("Failed to execute SQL from saved report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SQL 执行失败: {e}",
        )

    raw_res = result_str.strip()
    
    # 尝试进行 JSON 结果标准化解析（复用 chatbi_sql_execute 的转换逻辑）
    try:
        parsed = json.loads(raw_res)
        if isinstance(parsed, dict) and ("[Validation Failed]" in raw_res or "[Permission Denied]" in raw_res or "[Security Error]" in raw_res):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=parsed)
            
        # 若传入了会话ID，写入缓存供大模型下一轮做可视化复用
        if conversation_id:
            try:
                from app.services.ai.memory_service import memory_service
                cache_payload = {
                    "sql": sql_to_execute,
                    "data_source": report.data_source,
                    "dataset_name": None,
                    "rows": parsed,
                    "params": resolved_params,
                    "report_id": report.id,
                    "report_title": report.title,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                    "trace_id": None,
                }
                await memory_service.set_last_data_result(str(user_id), conversation_id, cache_payload)
            except Exception as cache_err:
                logger.warning("Failed to save report data to memory_service cache: %s", cache_err)

        return StandardResponse(data=parsed)
    except json.JSONDecodeError:
        pass

    # 如果是文本类输出（非标准 JSON 格式，如报错信息）
    if raw_res.startswith("[Validation Failed]") or raw_res.startswith("[Permission Denied]") or raw_res.startswith("[Security Error]"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=raw_res)
        
    return StandardResponse(data={"rows": raw_res})
