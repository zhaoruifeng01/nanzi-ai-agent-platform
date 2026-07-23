from app.services.ai.agent_service import AgentService
from app.services.ai.runtime.agentscope.stream_reconcile import suppress_quick_suggestions


def test_quick_suggestions_are_forbidden_only_for_automatic_delivery_contexts():
    assert not AgentService._should_forbid_quick_suggestions({})
    assert not AgentService._should_forbid_quick_suggestions({"is_scheduled_task": False})
    assert AgentService._should_forbid_quick_suggestions({"is_scheduled_task": True})
    assert AgentService._should_forbid_quick_suggestions({"is_subscription_task": True})
    assert AgentService._should_forbid_quick_suggestions({"quick_suggestions_forbidden": "true"})
    assert not AgentService._should_forbid_quick_suggestions({"quick_suggestions_forbidden": "false"})


def test_non_interactive_delivery_suppresses_quick_blocks_and_links():
    content = """结果已生成。

### 💬 您可能还想了解
---
- [🙋 查看趋势](quick:查看趋势)
- [🙋 对比明细](quick:对比明细)
"""

    cleaned = suppress_quick_suggestions(content)

    assert cleaned == "结果已生成。"
    assert "quick:" not in cleaned
