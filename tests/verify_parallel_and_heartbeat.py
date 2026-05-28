import asyncio
import time
import json
import os
import sys

# 确保能找到 app 模块
sys.path.append(os.getcwd())

from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import AIMessage
from app.services.ai.executors.data_executor import DataQueryExecutor
from app.schemas.agent import ChatConfig

async def verify():
    # 1. 模拟配置
    config = ChatConfig(
        agent_id="test-agent", agent_name="TestAgent",
        model_name="gpt-4", temperature=0,
        system_prompt="You are a helper.",
        tools=["slow_tool_1", "slow_tool_2"],
        capabilities=["data_query"]
    )

    # 2. 模拟两个“慢工具”，每个耗时 3 秒
    async def slow_tool_func(args):
        await asyncio.sleep(3)
        return f"Result of tool: {args}"

    tool_1 = MagicMock()
    tool_1.name = "slow_tool_1"
    tool_1.ainvoke = AsyncMock(side_effect=slow_tool_func)
    
    tool_2 = MagicMock()
    tool_2.name = "slow_tool_2"
    tool_2.ainvoke = AsyncMock(side_effect=slow_tool_func)

    # 3. 模拟 LLM：一次性要求调用这两个工具
    mock_response = AIMessage(
        content="I will call two slow tools.",
        tool_calls=[
            {"name": "slow_tool_1", "args": {"p": 1}, "id": "c1"},
            {"name": "slow_tool_2", "args": {"p": 2}, "id": "c2"}
        ]
    )
    
    # 4. 设置 Executor
    executor = DataQueryExecutor(config=config, trace_id="verify-trace", trace_buffer=[])
    
    # 5. Patch 依赖项
    with patch("app.services.ai.config.AgentConfigProvider.get_configured_llm") as mock_get_llm_raw, \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tool") as mock_get_tool, \
         patch("app.services.ai.tools.registry.ToolRegistry.get_tools") as mock_get_tools, \
         patch("app.services.config_service.ConfigService.get") as mock_config_get, \
         patch("app.services.ai.config.AgentConfigProvider.get_dataset_menu") as mock_get_menu:

        # 模拟 LLM 对象
        mock_llm = MagicMock()
        
        # 第一次返回工具调用，第二次返回结束
        stopping_response = AIMessage(content="I have the results.")
        mock_llm.ainvoke = AsyncMock(side_effect=[mock_response, stopping_response])
        mock_llm.bind_tools.return_value = mock_llm
        
        # 模拟 astream 
        async def mock_astream(*args, **kwargs):
            yield AIMessage(content="Final Done.")
            await asyncio.sleep(0.1) # 稍微停顿确保生成器能运行
        mock_llm.astream = mock_astream
        
        # 设置工厂函数返回这个 mock_llm
        mock_get_llm_raw.return_value = mock_llm
        
        mock_get_tools.return_value = [tool_1, tool_2]
        mock_get_menu.return_value = "Menu"
        mock_config_get.return_value = "5"
        
        def side_effect_get_tool(name):
            if "1" in name: return tool_1
            return tool_2
        mock_get_tool.side_effect = side_effect_get_tool

        print(f"🚀 开始执行验证测试 (模拟两个 3秒 任务)...")
        start_time = time.time()
        
        async for event in executor.execute([{"role": "user", "content": "run"}]):
            if event.get("type") == "log":
                status = event.get("status")
                title = event.get("title")
                print(f"⏰ [{time.time()-start_time:.1f}s] Log: {title} (Status: {status})")
            elif event.get("content"):
                print(f"💬 [{time.time()-start_time:.1f}s] Content: {event['content']}")

        total_time = time.time() - start_time
        print(f"\n✅ 测试结束")
        print(f"⏱️ 总耗时: {total_time:.2f} 秒")
        
        if total_time < 5:
            print("💪 [成功] 并行性验证：两个 3秒 任务在 ~3 秒左右完成，远快于串行的 6 秒。\n")
        else:
            print("❌ [失败] 并行性验证：耗时超过预期。\n")

if __name__ == "__main__":
    asyncio.run(verify())