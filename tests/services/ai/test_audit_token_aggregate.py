from datetime import datetime

from app.schemas.agent import AgentExecutionStep
from app.services.ai.audit import aggregate_tokens_from_trace_buffer


def _step(event_type: str, prompt=0, completion=0, total=0) -> AgentExecutionStep:
    return AgentExecutionStep(
        step_number=1,
        event_type=event_type,
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        timestamp=datetime.now(),
    )


def test_aggregate_sums_llm_steps_only():
    buffer = [
        _step("thought", prompt=100, completion=50, total=150),
        _step("tool_call", prompt=999, completion=999, total=999),
        _step("synthesis", prompt=20, completion=10, total=30),
    ]
    p, c, t = aggregate_tokens_from_trace_buffer(buffer)
    assert (p, c, t) == (120, 60, 180)


def test_aggregate_ignores_zero_token_synthesis_after_thought():
    """ReAct 首轮直答：synthesis 步骤 Token 为 0，不应重复计入。"""
    buffer = [
        _step("thought", prompt=80, completion=40, total=120),
        _step("synthesis", prompt=0, completion=0, total=0),
    ]
    p, c, t = aggregate_tokens_from_trace_buffer(buffer)
    assert (p, c, t) == (80, 40, 120)


def test_aggregate_orphan_total_when_no_breakdown():
    buffer = [_step("synthesis", total=200)]
    p, c, t = aggregate_tokens_from_trace_buffer(buffer)
    assert (p, c, t) == (0, 0, 200)


def test_aggregate_total_equals_prompt_plus_completion():
    buffer = [
        _step("thought", prompt=10, completion=5, total=999),
        _step("synthesis", prompt=3, completion=2, total=888),
    ]
    p, c, t = aggregate_tokens_from_trace_buffer(buffer)
    assert t == p + c


def test_aggregate_includes_followup_and_multi_agent_synthesis():
    buffer = [
        _step("synthesis", prompt=50, completion=25, total=75),
        _step("synthesis", prompt=10, completion=5, total=15),
    ]
    p, c, t = aggregate_tokens_from_trace_buffer(buffer)
    assert (p, c, t) == (60, 30, 90)
