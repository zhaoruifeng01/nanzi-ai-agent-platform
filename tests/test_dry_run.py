import unittest
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from typing import List, Dict, Any

from app.services.ai.executors.data_executor import DataQueryExecutor
from app.schemas.agent import ChatConfig, AgentExecutionStep


@pytest.fixture(scope="function", autouse=True)
async def init_infrastructure():
    """Override global infrastructure initialization to keep these executor tests offline."""
    with patch("app.core.database.init_db", new_callable=AsyncMock), \
         patch("app.core.database.close_db", new_callable=AsyncMock), \
         patch("app.core.redis.init_redis", new_callable=AsyncMock), \
         patch("app.core.redis.close_redis", new_callable=AsyncMock), \
         patch("app.core.orm.AsyncSessionLocal", new_callable=MagicMock):
        yield


class TestDryRun(unittest.IsolatedAsyncioTestCase):
    async def test_dry_run_sql_execution(self):
        # 1. Setup Config and Mock
        config = ChatConfig(
            agent_id="test", 
            agent_name="TestAgent",
            model_name="test-model",
            tools=["execute_sql_query"],
            system_prompt="test",
            temperature=0.0
        )
        debug_options = {"dry_run": True}
        trace_buffer = []
        
        executor = DataQueryExecutor(config, "trace-123", trace_buffer, debug_options)
        
        # 2. Mock Tool Call
        tool_call = {
            "name": "execute_sql_query",
            "args": {"query": "SELECT * FROM users"},
            "id": "call_1"
        }
        
        # 3. Call _dispatch_tool_safe directly (unit test approach)
        # It needs a list of tools, but in dry run it shouldn't access them if name matches
        _, output, _ = await executor._dispatch_tool_safe(tool_call, tools=[])
        
        # 4. Verify
        print(f"Result: {output}")
        self.assertIn("[DRY RUN MODE]", str(output))
        self.assertIn("SELECT * FROM users", str(output))

    async def test_normal_run_sql_execution(self):
        # 1. Setup Config
        config = ChatConfig(
            agent_id="test", 
            agent_name="TestAgent", 
            model_name="test", 
            tools=["execute_sql_query"],
            system_prompt="test",
            temperature=0.0
        )
        debug_options = {"dry_run": False}
        trace_buffer = []
        
        executor = DataQueryExecutor(config, "trace-123", trace_buffer, debug_options)
        
        # 2. Mock Tools
        mock_tool = AsyncMock()
        mock_tool.name = "execute_sql_query"
        mock_tool.ainvoke.return_value = "Real Result"
        
        tool_call = {
            "name": "execute_sql_query",
            "args": {"query": "SELECT * FROM users"},
            "id": "call_1"
        }
        
        # 3. Call
        _, output, _ = await executor._dispatch_tool_safe(tool_call, tools=[mock_tool])
        
        # 4. Verify
        self.assertEqual(output, "Real Result")
        mock_tool.ainvoke.assert_called_once()

    async def test_tool_execution_timeout_returns_tool_error(self):
        config = ChatConfig(
            agent_id="test",
            agent_name="TestAgent",
            model_name="test",
            tools=["execute_sql_query"],
            system_prompt="test",
            temperature=0.0
        )
        executor = DataQueryExecutor(config, "trace-123", [], {"dry_run": False})

        mock_tool = AsyncMock()
        mock_tool.name = "execute_sql_query"

        async def slow_ainvoke(_args):
            await asyncio.sleep(0.05)
            return "late"

        mock_tool.ainvoke.side_effect = slow_ainvoke
        tool_call = {
            "name": "execute_sql_query",
            "args": {"query": "SELECT * FROM users"},
            "id": "call_1"
        }

        with patch("app.services.config_service.ConfigService.get", AsyncMock(return_value="0.01")):
            _, output, _ = await executor._dispatch_tool_safe(tool_call, tools=[mock_tool])

        self.assertIn("[TOOL_ERROR]", str(output))
        self.assertIn("timed out", str(output))

if __name__ == "__main__":
    unittest.main()
