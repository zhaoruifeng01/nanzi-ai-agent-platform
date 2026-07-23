from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.config_service import ConfigService


pytestmark = pytest.mark.no_infrastructure


@pytest.fixture(autouse=True)
def reset_config_cache():
    ConfigService.invalidate_cache()
    yield
    ConfigService.invalidate_cache()


def _session_context(rows):
    result = MagicMock()
    result.fetchall.return_value = rows
    session = AsyncMock()
    session.execute.return_value = result
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    return session, context


@pytest.mark.asyncio
async def test_get_loads_full_table_once_for_multiple_and_missing_keys():
    session, context = _session_context(
        [
            ("llm_model_name", "glm-5.2", "model", "ai", False),
            ("agent_prompt_cache_boundary_enabled", "false", "prompt", "ai", False),
        ]
    )

    with patch("app.services.config_service.AsyncSessionLocal", return_value=context):
        assert await ConfigService.get("llm_model_name") == "glm-5.2"
        assert await ConfigService.get("agent_prompt_cache_boundary_enabled") == "false"
        assert await ConfigService.get("missing_key", "default") == "default"

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_negative_caches_an_empty_config_table():
    session, context = _session_context([])

    with patch("app.services.config_service.AsyncSessionLocal", return_value=context):
        assert await ConfigService.get("missing_a", "a") == "a"
        assert await ConfigService.get("missing_b", "b") == "b"

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_uses_caller_session_when_provided():
    result = MagicMock()
    result.fetchall.return_value = [
        ("llm_model_name", "glm-5.2", "model", "ai", False),
    ]
    session = AsyncMock()
    session.execute.return_value = result

    with patch("app.services.config_service.AsyncSessionLocal") as session_factory:
        configs = await ConfigService.get_all_from_db(db=session)

    assert configs["llm_model_name"]["value"] == "glm-5.2"
    session.execute.assert_awaited_once()
    session_factory.assert_not_called()
