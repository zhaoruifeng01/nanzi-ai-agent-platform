from __future__ import annotations

import re
import uuid


def _clean_key_part(value: str | None, fallback_prefix: str) -> str:
    raw = value or f"{fallback_prefix}_{uuid.uuid4().hex[:12]}"
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    return cleaned or f"{fallback_prefix}_{uuid.uuid4().hex[:12]}"


def build_workspace_key(trace_id: str | None, conversation_id: str | None = None) -> str:
    trace_part = _clean_key_part(trace_id, "trace")
    if not conversation_id:
        return trace_part
    return f"{trace_part}__{_clean_key_part(conversation_id, 'conversation')}"

