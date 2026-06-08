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


class NamedLegacyTool:
    description = "Named legacy tool"

    def __init__(self, name: str):
        self.name = name

    async def ainvoke(self, kwargs):
        return "ok"


@pytest.mark.asyncio
async def test_runtime_tool_spec_from_legacy_tool_invokes_ainvoke():
    from app.services.ai.runtime.agentscope.tools import runtime_tool_spec_from_legacy_tool

    spec = runtime_tool_spec_from_legacy_tool(FakeLegacyTool(), source_type="static")

    assert spec.name == "fake_search"
    assert spec.description == "Search fake data"
    assert spec.parameters_schema["required"] == ["query"]
    assert await spec.invoke({"query": "abc"}) == "found:abc"


def test_legacy_runtime_tool_specs_do_not_infer_dangerous_scope():
    from app.services.ai.runtime.agentscope.tools import runtime_tool_spec_from_legacy_tool

    former_dangerous_names = [
        "execute_sql_query",
        "system_http_request",
        "write_file",
        "exec_command",
        "manage_process",
        "create_skills",
    ]

    specs = [
        runtime_tool_spec_from_legacy_tool(NamedLegacyTool(name), source_type="static")
        for name in former_dangerous_names
    ]

    assert [spec.permission_scope for spec in specs] == ["ask"] * len(former_dangerous_names)


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


@pytest.mark.asyncio
async def test_tool_registry_maps_legacy_system_tool_names_to_agentscope_builtins():
    from agentscope.tool import Bash, Grep, Read, Write

    from app.services.ai.tools.registry import ToolRegistry

    specs = await ToolRegistry.get_runtime_tools(
        ["exec_command", "read_file", "write_file", "search_text"]
    )

    assert [spec.name for spec in specs] == ["Bash", "Read", "Write", "Grep"]
    assert isinstance(specs[0].native_tool, Bash)
    assert isinstance(specs[1].native_tool, Read)
    assert isinstance(specs[2].native_tool, Write)
    assert isinstance(specs[3].native_tool, Grep)
    assert [spec.permission_scope for spec in specs] == ["ask", "read", "ask", "read"]


@pytest.mark.asyncio
async def test_tool_registry_exposes_configurable_agentscope_edit_and_glob_tools():
    from agentscope.tool import Edit, Glob

    from app.services.ai.tools.registry import ToolRegistry

    specs = await ToolRegistry.get_runtime_tools(["edit_file", "glob_files"])

    assert [spec.name for spec in specs] == ["Edit", "Glob"]
    assert isinstance(specs[0].native_tool, Edit)
    assert isinstance(specs[1].native_tool, Glob)
