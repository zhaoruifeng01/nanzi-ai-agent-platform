import pytest


pytestmark = pytest.mark.no_infrastructure


@pytest.mark.asyncio
async def test_runtime_tool_spec_executes_callable_and_records_metadata():
    from app.services.ai.runtime.agentscope.tools import RuntimeToolSpec

    async def echo_tool(query: str) -> str:
        return f"echo:{query}"

    spec = RuntimeToolSpec(
        name="echo_tool",
        description="Echo a query",
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        source_type="static",
        callable=echo_tool,
        permission_scope="read",
        timeout_seconds=3.0,
    )

    result = await spec.invoke({"query": "hello"})

    assert result == "echo:hello"
    assert spec.is_read_only is True


@pytest.mark.asyncio
async def test_agentscope_tool_wrapper_exposes_tool_shape_and_invokes_spec():
    from app.services.ai.runtime.agentscope.tools import (
        AgentScopeRuntimeTool,
        RuntimeToolSpec,
    )

    async def sum_tool(left: int, right: int) -> int:
        return left + right

    spec = RuntimeToolSpec(
        name="sum_tool",
        description="Add two numbers",
        parameters_schema={
            "type": "object",
            "properties": {
                "left": {"type": "integer"},
                "right": {"type": "integer"},
            },
            "required": ["left", "right"],
        },
        source_type="static",
        callable=sum_tool,
        permission_scope="read",
    )

    tool = AgentScopeRuntimeTool(spec)

    assert tool.name == "sum_tool"
    assert tool.description == "Add two numbers"
    assert tool.input_schema["required"] == ["left", "right"]
    assert tool.is_read_only is True
    assert await tool(left=1, right=2) == "3"


def test_build_toolkit_returns_agent_scope_toolkit_when_available(monkeypatch):
    from app.services.ai.runtime.agentscope.tools import RuntimeToolSpec, build_toolkit

    class FakeToolkit:
        def __init__(self, tools):
            self.tools = tools

    monkeypatch.setattr(
        "app.services.ai.runtime.agentscope.tools._load_agentscope_toolkit",
        lambda: FakeToolkit,
    )

    toolkit = build_toolkit(
        [
            RuntimeToolSpec(
                name="noop",
                description="No-op",
                parameters_schema={"type": "object", "properties": {}},
                source_type="static",
                callable=lambda: "ok",
            )
        ]
    )

    assert isinstance(toolkit, FakeToolkit)
    assert [tool.name for tool in toolkit.tools] == ["noop"]


@pytest.mark.asyncio
async def test_build_toolkit_integrates_with_real_agentscope_toolkit():
    pytest.importorskip("agentscope.tool")

    from app.services.ai.runtime.agentscope.tools import RuntimeToolSpec, build_toolkit

    toolkit = build_toolkit(
        [
            RuntimeToolSpec(
                name="noop",
                description="No-op",
                parameters_schema={"type": "object", "properties": {}},
                source_type="static",
                callable=lambda: "ok",
                permission_scope="read",
            )
        ]
    )

    schemas = await toolkit.get_tool_schemas()

    assert schemas[0]["function"]["name"] == "noop"
    assert schemas[0]["function"]["description"] == "No-op"
