import pytest
import json
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.ai.tools.generic_api import GenericApiToolFactory
from app.models.tool import SysApiTool

@pytest.fixture
def mock_tool_config():
    return SysApiTool(
        name="test_get_user",
        description="Get user details",
        method="GET",
        url_template="http://api.example.com/users/{user_id}",
        parameter_schema={
            "properties": {
                "user_id": {"type": "integer", "description": "User ID"},
                "include_details": {"type": "boolean", "description": "Detailed info", "required": False, "default": False}
            },
            "required": ["user_id"]
        },
        headers={"X-Test": "HeaderValue"}
    )

def test_create_tool_schema_parsing(mock_tool_config):
    """测试动态生成工具的参数校验架构"""
    tool = GenericApiToolFactory.create_tool(mock_tool_config)
    
    assert tool.name == "test_get_user"
    assert "user_id" in tool.args_schema.model_fields
    assert "include_details" in tool.args_schema.model_fields
    
    # 验证字段类型
    fields = tool.args_schema.model_fields
    assert fields["user_id"].annotation == int
    assert fields["include_details"].annotation == bool
    # 验证默认值
    assert fields["include_details"].default is False

@pytest.mark.asyncio
async def test_execute_request_get_with_path_substitution(mock_tool_config):
    """测试 GET 请求：路径参数替换与查询参数拼接"""
    params = {"user_id": 123, "include_details": True}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"id": 123, "name": "John"})
        
        result = await GenericApiToolFactory._execute_request(mock_tool_config, params)
        
        # 验证 URL 替换和参数传递
        # user_id 被替换到 URL 中，不再出现在 params 里
        # include_details 作为查询参数传递
        args, kwargs = mock_get.call_args
        assert args[0] == "http://api.example.com/users/123"
        assert kwargs["params"] == {"include_details": True}
        assert kwargs["headers"]["X-Test"] == "HeaderValue"
        
        assert json.loads(result)["name"] == "John"

@pytest.mark.asyncio
async def test_execute_request_post_json_body():
    """测试 POST 请求：参数作为 JSON Body 传递"""
    config = SysApiTool(
        name="create_user",
        method="POST",
        url_template="http://api.example.com/users",
        parameter_schema={
            "properties": {
                "username": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
    )
    params = {"username": "alice", "age": 25}
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = httpx.Response(201, json={"status": "created"})
        
        await GenericApiToolFactory._execute_request(config, params)
        
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == "http://api.example.com/users"
        assert kwargs["json"] == params

@pytest.mark.asyncio
async def test_execute_request_error_handling(mock_tool_config):
    """测试执行过程中的异常处理"""
    params = {"user_id": 999}
    
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection failed")):
        result = await GenericApiToolFactory._execute_request(mock_tool_config, params)
        assert "[Execution Error]" in result
        assert "Connection failed" in result

def test_schema_parsing_simple_dict():
    """测试简化的 Schema 结构解析"""
    config = SysApiTool(
        name="simple_tool",
        parameter_schema={
            "q": "search query",
            "page": {"type": "integer", "description": "page number"}
        }
    )
    tool = GenericApiToolFactory.create_tool(config)
    fields = tool.args_schema.model_fields
    assert "q" in fields
    assert "page" in fields
    assert fields["page"].annotation == int
