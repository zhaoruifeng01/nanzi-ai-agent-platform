import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from app.services.ai.executors.chat_executor import GeneralChatExecutor
from app.schemas.agent import ChatConfig

@pytest.mark.asyncio
async def test_dual_model_execution_flow():
    """
    验证双模型执行流：
    1. 编排模型 (gpt-4o) 负责调用工具。
    2. 合成模型 (deepseek) 负责最终回复。
    """
    config = ChatConfig(
        agent_id="test-dual",
        agent_name="DualAgent",
        model_name="gpt-4o", # Orchestrator
        temperature=0.0,
        synthesis_model_name="deepseek-v3.2", # Synthesizer
        synthesis_temperature=0.7,
        system_prompt="You are a helper.",
        tools=["test_tool"]
    )

    # 1. Mock Orchestrator Response (Tool Call)
    # Note: In streaming mode, chunks usually don't have all fields populated at once,
    # but for mock simplicity we yield full messages.
    msg_call_tool = AIMessage(
        content="I will call the tool.",
        tool_calls=[{"name": "test_tool", "args": {"input": "val"}, "id": "call_1"}]
    )
    msg_orch_done = AIMessage(content="Done orchestration.")

    # 2. Mock Synthesizer Response (Final Answer)
    msg_final = AIMessage(content="Final Answer from DeepSeek")

    # Mock tools
    mock_tool = AsyncMock()
    mock_tool.name = "test_tool"
    mock_tool.ainvoke.return_value = "Result Data"

    # Mock Config Provider
    with patch("app.services.ai.config.AgentConfigProvider.get_configured_llm", new_callable=AsyncMock) as mock_get_orch, \
         patch("app.services.ai.config.AgentConfigProvider.get_synthesis_llm", new_callable=AsyncMock) as mock_get_syn, \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools", new_callable=AsyncMock) as mock_get_tools, \
         patch("app.services.config_service.ConfigService.get", new_callable=AsyncMock) as mock_config_get:

        # Orchestrator setup
        mock_orch = MagicMock()
        mock_orch.bind_tools.return_value = mock_orch
        
        # Define async generators for orchestrator turns
        async def gen_turn_1(*args, **kwargs):
            yield msg_call_tool
            
        async def gen_turn_2(*args, **kwargs):
            yield msg_orch_done

        # Use side_effect to return different generators for sequential calls
        # Note: GeneralChatExecutor might loop.
        mock_orch.astream.side_effect = [gen_turn_1(), gen_turn_2()]
        
        mock_get_orch.return_value = mock_orch

        # Synthesizer setup
        mock_syn = MagicMock()
        mock_syn.model_name = "deepseek-v3.2"  # Set model_name string for Pydantic validation
        async def mock_astream(*args, **kwargs):
            yield msg_final
        mock_syn.astream.side_effect = mock_astream
        mock_get_syn.return_value = mock_syn

        mock_get_tools.return_value = [mock_tool]
        mock_config_get.return_value = "5"

        executor = GeneralChatExecutor(config=config, trace_id="trace-dual", trace_buffer=[])
        
        events = []
        async for chunk in executor.execute([{"role": "user", "content": "Help me"}]):
            events.append(chunk)

        # Verification
        # 1. Orchestrator was called via astream (for logic/tool call)
        assert mock_orch.astream.called
        
        # 2. Synthesizer was called via astream (for final streaming response)
        assert mock_syn.astream.called
        
        # 3. Final content matches synthesizer
        final_content = "".join([e["content"] for e in events if "content" in e])
        assert "Final Answer from DeepSeek" in final_content

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dual_model_execution_flow())