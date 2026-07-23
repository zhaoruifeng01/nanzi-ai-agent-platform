from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any

try:
    from app.core.config import settings as _settings

    _DEFAULT_ENABLED: bool = bool(getattr(_settings, "CHAT_STREAM_DEBUG", True))
except Exception:  # pragma: no cover - config 未就绪时退回默认
    _DEFAULT_ENABLED = True

# 请求级开关:默认取环境变量 CHAT_STREAM_DEBUG;请求入口可用 set_stream_debug_enabled 覆盖。
_stream_debug_var: ContextVar[bool] = ContextVar(
    "chat_stream_debug_enabled",
    default=_DEFAULT_ENABLED,
)


def set_stream_debug_enabled(enabled: bool) -> None:
    """请求级覆盖 ChatStreamDebug 日志开关(在请求入口调用)。"""
    _stream_debug_var.set(bool(enabled))


def log_chat_stream_stage(
    logger: logging.Logger,
    *,
    event_type: str,
    title: str,
    trace_id: str | None = None,
    conversation_id: str | None = None,
    phase: str | None = None,
    status: str | None = None,
    elapsed_ms: float | None = None,
    agent_name: str | None = None,
    model_name: str | None = None,
    reply_id: str | None = None,
    fields: dict[str, Any] | None = None,
) -> None:
    """Emit one backend log line for a frontend-visible chat stream stage."""
    if not _stream_debug_var.get():
        return
    payload: dict[str, Any] = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "event_type": event_type,
        "title": title,
    }
    if phase:
        payload["phase"] = phase
    if status:
        payload["status"] = status
    if trace_id:
        payload["trace_id"] = trace_id
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if elapsed_ms is not None:
        payload["elapsed_ms"] = round(float(elapsed_ms), 1)
    if agent_name:
        payload["agent_name"] = agent_name
    if model_name:
        payload["model_name"] = model_name
    if reply_id:
        payload["reply_id"] = reply_id
    if fields:
        payload.update(fields)

    logger.info("[ChatStreamDebug] %s", json.dumps(payload, ensure_ascii=False, default=str))
