from app.services.ai.executors.prompts import DataQueryPrompts


def test_build_clarification_fallback_for_followup_missing_context():
    content = DataQueryPrompts.build_clarification_fallback(
        "可视化分析一下",
        "请求类别 LLM 未返回有效结果；检测到结果追问但没有可信的近期可复用结构化查询结果",
        "用户: 查询算力SU 1-6月回款率\n助手: | 月份 | 回款率 |",
    )
    assert "继续分析或可视化" in content
    assert "### 💬 您可以这样继续" in content
    assert "(quick:" in content
    assert "算力SU" in content


def test_build_clarification_fallback_for_general_chat():
    content = DataQueryPrompts.build_clarification_fallback(
        "你好，你是谁",
        "当前请求不是明确的 ChatBI 查数请求，需要用户补充想查询的业务数据、指标、维度或时间范围",
        "",
    )
    assert "PUE" in content
    assert DataQueryPrompts.has_quick_suggestions(content)


def test_build_missing_reusable_result_fallback_includes_quick_buttons():
    content = DataQueryPrompts.build_missing_reusable_result_fallback(
        "用户: 查询算力SU回款趋势",
    )
    assert "结构化查询结果" in content
    assert "(quick:对刚刚的查询结果做可视化分析)" in content
    assert "(quick:查询算力SU回款趋势)" in content
