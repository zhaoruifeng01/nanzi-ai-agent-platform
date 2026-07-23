from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.schemas.agent import ChatConfig
from app.services.ai.runners.assistant_agent_runner import AssistantAgentRunner


pytestmark = pytest.mark.no_infrastructure


@pytest.mark.asyncio
async def test_preloaded_delegable_agents_skip_runner_database_lookup():
    config = ChatConfig(
        agent_id="sys-agent-chat",
        agent_name="main",
        model_name="glm-5.2",
        temperature=0.2,
        system_prompt="prompt",
        tools=[],
        capabilities=["chat"],
        engine_config={},
    )
    delegable = SimpleNamespace(
        id="agent-data",
        name="chat-bi",
        display_name="Data Assistant",
        capabilities=["data_query"],
        sort_order=10,
    )
    runner = AssistantAgentRunner(
        config=config,
        trace_id="trace-preload",
        trace_buffer=[],
        runtime_context={"delegable_agents": [delegable]},
    )

    with patch(
        "app.services.ai.runners.assistant_agent_runner.AsyncSessionLocal"
    ) as session_factory:
        names, candidates = await runner._resolve_available_sub_agent_delegation_info()

    assert "chat-bi" in names
    assert candidates == {"data_query": ["chat-bi"]}
    session_factory.assert_not_called()
