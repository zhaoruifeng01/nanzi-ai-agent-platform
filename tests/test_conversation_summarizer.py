"""Conversation summarizer structured memory output."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai.conversation_summarizer import ConversationSummarizer

pytestmark = pytest.mark.no_infrastructure


class FakeResponse:
    content = """
    {
      "title": "记忆设计",
      "summary": "讨论了 session summary 和 daily summary 的分层设计。",
      "key_facts": ["一个 conversation_id 对应一条 session summary"],
      "decisions": ["保留 conversation_id", "新增 daily summary"],
      "open_items": ["后续补管理 UI"],
      "entities": ["memory_search", "Redis"],
      "memory_type": "project"
    }
    """


@pytest.mark.asyncio
async def test_summarize_returns_structured_memory_fields():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=FakeResponse())

    with patch(
        "app.services.ai.conversation_summarizer.get_llm_async",
        new_callable=AsyncMock,
        return_value=llm,
    ):
        result = await ConversationSummarizer.summarize(
            [{"role": "user", "content": "记忆 summary 设计怎么做？"}]
        )

    assert result["title"] == "记忆设计"
    assert result["summary"].startswith("讨论了")
    assert result["key_facts"] == ["一个 conversation_id 对应一条 session summary"]
    assert result["decisions"] == ["保留 conversation_id", "新增 daily summary"]
    assert result["open_items"] == ["后续补管理 UI"]
    assert result["entities"] == ["memory_search", "Redis"]
    assert result["memory_type"] == "project"
    prompt = llm.ainvoke.await_args.args[0][0].content
    assert "key_facts" in prompt
    assert "decisions" in prompt
    assert "open_items" in prompt
