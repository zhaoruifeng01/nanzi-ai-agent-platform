import pytest


pytestmark = pytest.mark.no_infrastructure


class FakeArgsSchema:
    @classmethod
    def model_json_schema(cls):
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }


class FakeLegacyTool:
    name = "fake_search"
    description = "Search fake data"
    args_schema = FakeArgsSchema

    async def ainvoke(self, kwargs):
        return f"found:{kwargs['query']}"


@pytest.mark.asyncio
async def test_runtime_tool_spec_from_legacy_tool_invokes_ainvoke():
    from app.services.ai.runtime.agentscope.tools import runtime_tool_spec_from_legacy_tool

    spec = runtime_tool_spec_from_legacy_tool(FakeLegacyTool(), source_type="static")

    assert spec.name == "fake_search"
    assert spec.description == "Search fake data"
    assert spec.parameters_schema["required"] == ["query"]
    assert await spec.invoke({"query": "abc"}) == "found:abc"


@pytest.mark.asyncio
async def test_tool_registry_exposes_runtime_tool_specs(monkeypatch):
    from app.services.ai.runtime.agentscope.tools import RuntimeToolSpec
    from app.services.ai.tools.registry import ToolRegistry

    monkeypatch.setitem(ToolRegistry._registry, "fake_search", FakeLegacyTool())

    spec = await ToolRegistry.get_runtime_tool("fake_search")

    assert isinstance(spec, RuntimeToolSpec)
    assert spec.name == "fake_search"
    assert await spec.invoke({"query": "abc"}) == "found:abc"


@pytest.mark.asyncio
async def test_tool_registry_runtime_tools_filters_unknown(monkeypatch):
    from app.services.ai.tools.registry import ToolRegistry

    monkeypatch.setitem(ToolRegistry._registry, "fake_search", FakeLegacyTool())

    specs = await ToolRegistry.get_runtime_tools(["fake_search", "missing_tool"])

    assert [spec.name for spec in specs] == ["fake_search"]
