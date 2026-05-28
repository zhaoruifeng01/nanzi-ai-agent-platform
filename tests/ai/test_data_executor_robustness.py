import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.ai.executors.data_executor import DataQueryExecutor
from langchain_core.messages import AIMessage, SystemMessage

@pytest.fixture(scope="function", autouse=True)
async def init_infrastructure():
    """Override global infrastructure initialization to keep this executor unit test offline."""
    with patch("app.core.database.init_db", new_callable=AsyncMock), \
         patch("app.core.database.close_db", new_callable=AsyncMock), \
         patch("app.core.redis.init_redis", new_callable=AsyncMock), \
         patch("app.core.redis.close_redis", new_callable=AsyncMock), \
         patch("app.core.orm.AsyncSessionLocal", new_callable=MagicMock):
        yield


@pytest.mark.asyncio
async def test_data_executor_react_nudge():
    """
    Verify that DataQueryExecutor nudges the model if it's "chatty" but doesn't call tools in Turn 1.
    """
    mock_config = MagicMock()
    mock_config.agent_name = "ChatBI"
    mock_config.system_prompt = "You are a Data Analysis Assistant. {dataset_menu}"
    mock_config.tools = ["get_dataset_schema", "execute_sql_query"]
    mock_config.model_name = "test-model"
    mock_config.temperature = 0.0
    mock_config.capabilities = ["data_query"]

    trace_id = "test-trace"
    trace_buffer = []
    
    executor = DataQueryExecutor(mock_config, trace_id, trace_buffer)
    
    # 1. Prepare Mock Responses (Must be > 50 chars to trigger nudge)
    procrastinating_response = MagicMock(spec=AIMessage)
    procrastinating_response.content = "好的，我理解您的需求是查询监控数据。为了能够给出准确的分析结果，我首先需要调用相关工具来获取数据库中 monitor 表的具体结构定义。请您稍等片刻。"
    procrastinating_response.tool_calls = []
    
    acting_response = MagicMock(spec=AIMessage)
    acting_response.content = ""
    acting_response.tool_calls = [{"name": "get_dataset_schema", "args": {"query": "monitor"}, "id": "call_1"}]
    
    stopping_response = MagicMock(spec=AIMessage) # Turn 3: Break the loop
    stopping_response.content = "I have the results now."
    stopping_response.tool_calls = []

    final_answer = MagicMock(spec=AIMessage)
    final_answer.content = "This is the final Answer"

    # 2. Mock model-with-tools astream
    model_with_tools = MagicMock()
    
    async def mock_astream_main(*args, **kwargs):
        # We need to simulate multiple turns. 
        # But DataQueryExecutor.execute recreates the model/stream? No, it uses the same one in the loop.
        # Wait, langchain models are usually stateless. 
        # In the loop:
        # async for chunk in model_with_tools.astream(langchain_messages):
        # We can use side_effect on astream to return different generators
        pass

    async def gen_1(*args, **kwargs): yield procrastinating_response
    async def gen_2(*args, **kwargs): yield acting_response
    async def gen_3(*args, **kwargs): yield stopping_response

    model_with_tools.astream.side_effect = [gen_1(), gen_2(), gen_3()]
    
    # model_with_tools is the result of bind_tools
    bound_model = MagicMock()
    bound_model.bind_tools.return_value = model_with_tools
    
    # 3. Mock synthesis LLM astream
    llm_syn = MagicMock()
    async def mock_astream_syn(*args, **kwargs):
        yield final_answer
    llm_syn.astream.side_effect = mock_astream_syn

    # 4. Patch context
    with patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", AsyncMock(return_value=bound_model)), \
         patch("app.services.ai.config.AgentConfigProvider.get_synthesis_llm", AsyncMock(return_value=llm_syn)), \
         patch("app.services.ai.config.AgentConfigProvider.get_dataset_menu", AsyncMock(return_value="Dataset: Test")), \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", AsyncMock(return_value=[MagicMock(name="get_dataset_schema", spec=["name", "ainvoke"])])), \
         patch("app.services.config_service.ConfigService.get", AsyncMock(return_value="5")):
        
        # Mock internal tool execution
        executor._dispatch_tool_safe = AsyncMock(return_value=({'name': 'get_dataset_schema', 'id': 'call_1', 'args': {'query': 'monitor'}}, "Schema YAML", 100.0))
        
        # Actually execute
        messages = [{"role": "user", "content": "帮我查一下监控数据"}]
        events = []
        async for chunk in executor.execute(messages):
            events.append(chunk)

        # Verification: 
        # astream should have been called three times
        assert model_with_tools.astream.call_count == 3
        
        # Check if the nudge message was added to history in the second call
        history_in_second_call = model_with_tools.astream.call_args_list[1][0][0]
        assert any("检测到你在描述计划但未调用工具" in str(m.content) for m in history_in_second_call)        
        assert not any(
            chunk.get("content") == procrastinating_response.content
            for chunk in events
        )
        print("\n✅ DataQueryExecutor Nudge Logic Verified with astream.")


@pytest.mark.asyncio
async def test_data_executor_followup_visualization_reuses_last_result_without_querying():
    """基于上一轮结果的可视化追问应直接分析历史结果，不应重新检索 schema 或执行 SQL。"""
    mock_config = MagicMock()
    mock_config.agent_name = "ChatBI"
    mock_config.system_prompt = "You are a Data Analysis Assistant. {dataset_menu}"
    mock_config.tools = ["get_dataset_schema", "execute_sql_query"]
    mock_config.model_name = "test-model"
    mock_config.temperature = 0.0
    mock_config.synthesis_model_name = None
    mock_config.synthesis_temperature = None
    mock_config.capabilities = ["data_query"]

    executor = DataQueryExecutor(
        mock_config,
        "trace-followup",
        [],
        user_info={"user_id": 1001},
        conversation_id="conv-1",
    )

    final_answer = MagicMock(spec=AIMessage)
    final_answer.content = "基于上一轮用户列表，已生成状态分布图。"
    llm_syn = MagicMock()

    async def mock_astream_syn(*args, **kwargs):
        yield final_answer

    llm_syn.astream.side_effect = mock_astream_syn
    last_result = {
        "sql": "select status, count(*) as total_count from users group by status",
        "dataset_name": "users",
        "data_source": "mysql_oa",
        "rows": [{"status": "启用", "total_count": 8}, {"status": "停用", "total_count": 2}],
    }

    with patch("app.services.ai.memory_service.memory_service.get_last_data_result", AsyncMock(return_value=last_result)) as mock_get_last, \
         patch("app.services.ai.config.AgentConfigProvider.get_synthesis_llm", AsyncMock(return_value=llm_syn)), \
         patch("app.services.ai.config.AgentConfigProvider.get_dataset_menu", AsyncMock(return_value="Dataset: Test")), \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", AsyncMock()) as mock_get_tools, \
         patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", AsyncMock()) as mock_get_llm:

        events = []
        async for chunk in executor.execute([
            {"role": "assistant", "content": "上一轮返回了用户列表。"},
            {"role": "user", "content": "可视化分析一下"},
        ]):
            events.append(chunk)

    assert mock_get_last.await_count == 1
    mock_get_tools.assert_not_called()
    mock_get_llm.assert_not_called()
    assert any(chunk.get("content") == final_answer.content for chunk in events)


@pytest.mark.asyncio
async def test_data_executor_stores_successful_sql_result_for_followups():
    """SQL 查询成功后应保存结构化结果，供下一轮可视化/分析追问复用。"""
    mock_config = MagicMock()
    mock_config.agent_name = "ChatBI"
    mock_config.system_prompt = "You are a Data Analysis Assistant. {dataset_menu}"
    mock_config.tools = ["execute_sql_query"]
    mock_config.model_name = "test-model"
    mock_config.temperature = 0.0
    mock_config.synthesis_model_name = None
    mock_config.synthesis_temperature = None
    mock_config.capabilities = ["data_query"]

    executor = DataQueryExecutor(
        mock_config,
        "trace-store",
        [],
        user_info={"user_id": 1001},
        conversation_id="conv-1",
    )

    acting_response = MagicMock(spec=AIMessage)
    acting_response.content = "<thought><sql_plan>{}</sql_plan></thought>"
    acting_response.tool_calls = [{
        "name": "execute_sql_query",
        "args": {
            "sql": "select status, count(*) as total_count from users group by status",
            "data_source": "mysql_oa",
            "dataset_name": "users",
        },
        "id": "call_sql",
    }]
    stopping_response = MagicMock(spec=AIMessage)
    stopping_response.content = "I have the results now."
    stopping_response.tool_calls = []

    model_with_tools = MagicMock()

    async def gen_1(*args, **kwargs):
        yield acting_response

    async def gen_2(*args, **kwargs):
        yield stopping_response

    model_with_tools.astream.side_effect = [gen_1(), gen_2()]
    bound_model = MagicMock()
    bound_model.bind_tools.return_value = model_with_tools

    final_answer = MagicMock(spec=AIMessage)
    final_answer.content = "用户状态分布已汇总。"
    llm_syn = MagicMock()

    async def mock_astream_syn(*args, **kwargs):
        yield final_answer

    llm_syn.astream.side_effect = mock_astream_syn
    sql_rows = [{"status": "启用", "total_count": 8}, {"status": "停用", "total_count": 2}]

    with patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", AsyncMock(return_value=bound_model)), \
         patch("app.services.ai.config.AgentConfigProvider.get_synthesis_llm", AsyncMock(return_value=llm_syn)), \
         patch("app.services.ai.config.AgentConfigProvider.get_dataset_menu", AsyncMock(return_value="Dataset: Test")), \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", AsyncMock(return_value=[MagicMock(name="execute_sql_query", spec=["name", "ainvoke"])])), \
         patch("app.services.config_service.ConfigService.get", AsyncMock(return_value="5")), \
         patch("app.services.ai.memory_service.memory_service.set_last_data_result", AsyncMock()) as mock_set_last:

        executor._dispatch_tool_safe = AsyncMock(return_value=(acting_response.tool_calls[0], sql_rows, 12.0))
        async for _ in executor.execute([{"role": "user", "content": "查询用户状态分布"}]):
            pass

    saved_payload = mock_set_last.await_args.args[2]
    assert mock_set_last.await_args.args[:2] == (1001, "conv-1")
    assert saved_payload["sql"] == "select status, count(*) as total_count from users group by status"
    assert saved_payload["dataset_name"] == "users"
    assert saved_payload["rows"] == sql_rows


@pytest.mark.asyncio
async def test_data_executor_stops_react_loop_after_successful_sql():
    """SQL 成功且无异常复核需求时，应直接进入汇总，不再额外跑一轮模型决策。"""
    mock_config = MagicMock()
    mock_config.agent_name = "ChatBI"
    mock_config.system_prompt = "You are a Data Analysis Assistant. {dataset_menu}"
    mock_config.tools = ["execute_sql_query"]
    mock_config.model_name = "test-model"
    mock_config.temperature = 0.0
    mock_config.synthesis_model_name = None
    mock_config.synthesis_temperature = None
    mock_config.capabilities = ["data_query"]

    executor = DataQueryExecutor(mock_config, "trace-fast-path", [], {"dry_run": False})

    acting_response = MagicMock(spec=AIMessage)
    acting_response.content = "<thought><sql_plan>{}</sql_plan></thought>"
    acting_response.tool_calls = [{
        "name": "execute_sql_query",
        "args": {
            "sql": "select status, count(*) as total_count from users group by status",
            "data_source": "mysql_oa",
            "dataset_name": "users",
        },
        "id": "call_sql",
    }]

    model_with_tools = MagicMock()

    async def gen_1(*args, **kwargs):
        yield acting_response

    async def gen_unexpected(*args, **kwargs):
        raise AssertionError("SQL 成功后不应该再进入下一轮模型决策")
        yield

    model_with_tools.astream.side_effect = [gen_1(), gen_unexpected()]
    bound_model = MagicMock()
    bound_model.bind_tools.return_value = model_with_tools

    final_answer = MagicMock(spec=AIMessage)
    final_answer.content = "用户状态分布已汇总。"
    llm_syn = MagicMock()

    async def mock_astream_syn(*args, **kwargs):
        yield final_answer

    llm_syn.astream.side_effect = mock_astream_syn

    with patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", AsyncMock(return_value=bound_model)), \
         patch("app.services.ai.config.AgentConfigProvider.get_synthesis_llm", AsyncMock(return_value=llm_syn)), \
         patch("app.services.ai.config.AgentConfigProvider.get_dataset_menu", AsyncMock(return_value="Dataset: Test")), \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", AsyncMock(return_value=[MagicMock(name="execute_sql_query", spec=["name", "ainvoke"])])), \
         patch("app.services.config_service.ConfigService.get", AsyncMock(return_value="5")):

        executor._dispatch_tool_safe = AsyncMock(return_value=(acting_response.tool_calls[0], [{"status": "启用", "total_count": 8}], 12.0))
        events = []
        async for chunk in executor.execute([{"role": "user", "content": "查询用户状态分布"}]):
            events.append(chunk)

    assert model_with_tools.astream.call_count == 1
    assert any(chunk.get("content") == final_answer.content for chunk in events)


@pytest.mark.asyncio
async def test_data_executor_followup_without_last_result_does_not_query_schema():
    """可视化追问缺少上一轮结构化结果时，应提示用户先查询数据，而不是把追问词拿去检索 schema。"""
    mock_config = MagicMock()
    mock_config.agent_name = "ChatBI"
    mock_config.system_prompt = "You are a Data Analysis Assistant. {dataset_menu}"
    mock_config.tools = ["get_dataset_schema", "execute_sql_query"]
    mock_config.model_name = "test-model"
    mock_config.temperature = 0.0
    mock_config.capabilities = ["data_query"]

    executor = DataQueryExecutor(
        mock_config,
        "trace-no-last-result",
        [],
        user_info={"user_id": 1001},
        conversation_id="conv-1",
    )

    with patch("app.services.ai.memory_service.memory_service.get_last_data_result", AsyncMock(return_value=None)), \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", AsyncMock()) as mock_get_tools, \
         patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", AsyncMock()) as mock_get_llm:

        events = []
        async for chunk in executor.execute([{"role": "user", "content": "可视化分析一下"}]):
            events.append(chunk)

    mock_get_tools.assert_not_called()
    mock_get_llm.assert_not_called()
    assert any("没有可复用的上一轮查询结果" in chunk.get("content", "") for chunk in events)

if __name__ == "__main__":
    asyncio.run(test_data_executor_react_nudge())
