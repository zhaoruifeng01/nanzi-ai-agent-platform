import pytest
from app.services.ai.tools.registry import ToolRegistry
from app.schemas.agent import ToolConfigItem

@pytest.mark.asyncio
async def test_get_tools_legacy_string_format():
    """验证传统的字符串列表格式工具加载"""
    tool_names = ["get_dataset_schema", "execute_sql_query"]
    tools = await ToolRegistry.get_tools(tool_names)
    
    assert len(tools) == 2
    assert tools[0].name == "get_dataset_schema"
    assert not hasattr(tools[0], "_runtime_config")

@pytest.mark.asyncio
async def test_get_tools_structured_config():
    """验证结构化 ToolConfigItem 格式工具加载及模型覆盖"""
    tool_configs = [
        ToolConfigItem(name="execute_sql_query", model_name="gpt-4o", temperature=0.1),
        "get_dataset_schema" # 混合模式测试
    ]
    
    tools = await ToolRegistry.get_tools(tool_configs)
    
    assert len(tools) == 2
    
    # 检查第一个工具是否有覆盖配置
    sql_tool = next(t for t in tools if t.name == "execute_sql_query")
    assert hasattr(sql_tool, "_runtime_config")
    assert sql_tool._runtime_config.model_name == "gpt-4o"
    assert sql_tool._runtime_config.temperature == 0.1
    
    # 检查第二个工具是否保持原始状态
    schema_tool = next(t for t in tools if t.name == "get_dataset_schema")
    assert not hasattr(schema_tool, "_runtime_config")

@pytest.mark.asyncio
async def test_get_tools_from_db_dict():
    """验证从数据库读取的字典格式工具加载（模拟真实场景）"""
    db_configs = [
        {
            "name": "system_http_request",
            "model_name": "deepseek-coder",
            "temperature": 0.0,
            "enabled": True
        }
    ]
    
    tools = await ToolRegistry.get_tools(db_configs)
    
    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "system_http_request"
    assert hasattr(tool, "_runtime_config")
    assert tool._runtime_config.model_name == "deepseek-coder"
    assert tool._runtime_config.temperature == 0.0

@pytest.mark.asyncio
async def test_tool_copy_isolation():
    """验证工具实例的配置是隔离的，不影响全局注册表中的实例"""
    config1 = [ToolConfigItem(name="execute_sql_query", model_name="model-A")]
    config2 = [ToolConfigItem(name="execute_sql_query", model_name="model-B")]
    
    tools1 = await ToolRegistry.get_tools(config1)
    tools2 = await ToolRegistry.get_tools(config2)
    
    assert tools1[0]._runtime_config.model_name == "model-A"
    assert tools2[0]._runtime_config.model_name == "model-B"
    
    # 再次获取原始工具，应该没有配置
    original_tool = await ToolRegistry.get_tool("execute_sql_query")
    assert not hasattr(original_tool, "_runtime_config")
