from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.agent import ChatConfig
from app.services.ai.config import AgentConfigProvider


pytestmark = pytest.mark.no_infrastructure


@pytest.mark.asyncio
async def test_load_model_registry_batches_active_models_on_caller_session():
    rows = [
        SimpleNamespace(
            model_id="glm-5.2-api",
            name="glm-5.2",
            api_key="secret",
            api_base_url="https://example.test/v1",
            type="llm",
        )
    ]
    scalars = MagicMock()
    scalars.all.return_value = rows
    result = MagicMock()
    result.scalars.return_value = scalars
    session = AsyncMock()
    session.execute.return_value = result

    with patch("app.services.ai.config.AsyncSessionLocal", create=True) as session_factory:
        registry = await AgentConfigProvider.load_model_registry(db=session)

    assert registry["glm-5.2"] is registry["glm-5.2-api"]
    assert registry["glm-5.2"]["api_base_url"] == "https://example.test/v1"
    session.execute.assert_awaited_once()
    session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_get_configured_llm_uses_preloaded_model_registry_without_query():
    config = ChatConfig(
        agent_id="main",
        agent_name="main",
        model_name="glm-5.2",
        temperature=0.2,
        system_prompt="prompt",
        tools=[],
        capabilities=["chat"],
        engine_config={},
    )
    registry = {
        "glm-5.2": {
            "model_id": "glm-5.2-api",
            "api_key": "model-key",
            "api_base_url": "https://example.test/v1",
        }
    }
    session = AsyncMock()
    llm_handle = object()

    with patch(
        "app.services.ai.config.ConfigService.get_all_from_db",
        new_callable=AsyncMock,
        return_value={},
    ) as get_configs, patch(
        "app.services.ai.config.get_llm",
        return_value=llm_handle,
    ) as get_llm:
        resolved = await AgentConfigProvider.get_configured_llm(
            streaming=True,
            config=config,
            db=session,
            model_registry=registry,
        )

    assert resolved is llm_handle
    get_configs.assert_awaited_once_with(db=session)
    session.execute.assert_not_awaited()
    get_llm.assert_called_once_with(
        streaming=True,
        api_key="model-key",
        base_url="https://example.test/v1",
        model="glm-5.2-api",
        temperature=0.2,
    )
