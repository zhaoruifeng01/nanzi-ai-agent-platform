from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal


ToolSourceType = Literal["static", "generic_api", "mcp", "class", "system"]


@dataclass(frozen=True)
class RuntimeToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    source_type: ToolSourceType
    callable: Callable[..., Any]
    permission_scope: str = "write"
    timeout_seconds: float | None = None

    @property
    def is_read_only(self) -> bool:
        return self.permission_scope == "read"

    async def invoke(self, arguments: dict[str, Any] | None = None) -> Any:
        arguments = arguments or {}
        result = self.callable(**arguments)
        if inspect.isawaitable(result):
            if self.timeout_seconds:
                return await asyncio.wait_for(result, timeout=self.timeout_seconds)
            return await result
        return result


class AgentScopeRuntimeTool:
    is_concurrency_safe = False
    is_external_tool = False
    is_state_injected = False
    is_mcp = False
    mcp_name = None

    def __init__(self, spec: RuntimeToolSpec) -> None:
        self.spec = spec
        self.name = spec.name
        self.description = spec.description
        self.input_schema = spec.parameters_schema
        self.is_read_only = spec.is_read_only

    async def check_permissions(self, tool_input: dict[str, Any], context: Any) -> Any:
        try:
            from agentscope.permission import PermissionBehavior, PermissionDecision
        except Exception:
            return None
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            reason="runtime permission checks are handled by platform middleware",
        )

    async def check_read_only(self, tool_input: dict[str, Any]) -> bool:
        return self.is_read_only

    def match_rule(self, rule_content: str | None, tool_input: dict[str, Any]) -> bool:
        return rule_content is None

    async def __call__(self, **kwargs: Any) -> str:
        return str(await self.spec.invoke(kwargs))


def _load_agentscope_toolkit():
    from agentscope.tool import Toolkit

    return Toolkit


def build_toolkit(tool_specs: list[RuntimeToolSpec]):
    toolkit_cls = _load_agentscope_toolkit()
    return toolkit_cls(tools=[AgentScopeRuntimeTool(spec) for spec in tool_specs])


def _schema_from_legacy_tool(tool: Any) -> dict[str, Any]:
    args_schema = getattr(tool, "args_schema", None)
    if args_schema is not None and hasattr(args_schema, "model_json_schema"):
        return args_schema.model_json_schema()
    input_schema = getattr(tool, "input_schema", None)
    if isinstance(input_schema, dict):
        return input_schema
    return {"type": "object", "properties": {}}


def runtime_tool_spec_from_legacy_tool(
    tool: Any,
    source_type: ToolSourceType,
    permission_scope: str = "write",
) -> RuntimeToolSpec:
    async def _invoke(**kwargs: Any) -> Any:
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(kwargs)
        if hasattr(tool, "arun"):
            return await tool.arun(**kwargs)
        if callable(tool):
            result = tool(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        raise TypeError(f"Tool {getattr(tool, 'name', repr(tool))} is not callable")

    name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
    if not name:
        raise ValueError("Legacy tool is missing a name")

    return RuntimeToolSpec(
        name=name,
        description=getattr(tool, "description", None) or getattr(tool, "__doc__", "") or "",
        parameters_schema=_schema_from_legacy_tool(tool),
        source_type=source_type,
        callable=_invoke,
        permission_scope=permission_scope,
    )
