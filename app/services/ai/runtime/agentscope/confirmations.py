from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


PENDING_CONFIRMATION_TTL_SECONDS = 600


@dataclass
class PendingAgentScopeConfirmation:
    request_id: str
    agent: Any
    runner: Any
    tools: list[Any]
    native_model: Any
    tool_call: Any
    reply_id: str
    trace_id: str
    user_id: str | None = None
    created_at: float = field(default_factory=time.time)
    state: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: float | None = None) -> bool:
        now = now or time.time()
        return now - self.created_at > PENDING_CONFIRMATION_TTL_SECONDS


class PendingAgentScopeConfirmationRegistry:
    def __init__(self) -> None:
        self._items: dict[str, PendingAgentScopeConfirmation] = {}

    def register(
        self,
        *,
        agent: Any,
        runner: Any,
        tools: list[Any],
        native_model: Any,
        tool_call: Any,
        reply_id: str,
        trace_id: str,
        user_id: str | None = None,
        state: dict[str, Any] | None = None,
    ) -> PendingAgentScopeConfirmation:
        self.prune()
        request = PendingAgentScopeConfirmation(
            request_id=f"perm_{uuid.uuid4().hex}",
            agent=agent,
            runner=runner,
            tools=tools,
            native_model=native_model,
            tool_call=tool_call,
            reply_id=reply_id,
            trace_id=trace_id,
            user_id=str(user_id) if user_id is not None else None,
            state=state or {},
        )
        self._items[request.request_id] = request
        return request

    def pop(self, request_id: str) -> PendingAgentScopeConfirmation | None:
        self.prune()
        request = self._items.pop(request_id, None)
        if request and request.is_expired():
            return None
        return request

    def peek(self, request_id: str) -> PendingAgentScopeConfirmation | None:
        self.prune()
        request = self._items.get(request_id)
        if request and request.is_expired():
            self._items.pop(request_id, None)
            return None
        return request

    def prune(self) -> None:
        now = time.time()
        expired = [
            request_id
            for request_id, request in self._items.items()
            if request.is_expired(now)
        ]
        for request_id in expired:
            self._items.pop(request_id, None)

    def clear(self) -> None:
        self._items.clear()


pending_agentscope_confirmations = PendingAgentScopeConfirmationRegistry()
