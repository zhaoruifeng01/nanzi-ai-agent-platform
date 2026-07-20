from pathlib import Path

import pytest

pytestmark = pytest.mark.no_infrastructure


def test_markdown_editor_exposes_ai_optimize_when_enabled():
    editor = Path("frontend/src/components/MarkdownEditor.vue").read_text()
    optimize = Path("frontend/src/components/PromptAiOptimize.vue").read_text()

    assert "enableOptimize" in editor
    assert "PromptAiOptimize" in editor
    assert "AI 润色" in optimize
    assert "/api/portal/prompts/optimize" in optimize
    assert "element:prompts:optimize" in optimize
    assert "应用此方案" in optimize


def test_agent_version_editor_enables_prompt_ai_optimize():
    drawer = Path("frontend/src/components/agent/AgentVersionEditorDrawer.vue").read_text()

    assert "MarkdownEditor" in drawer
    assert "enable-optimize" in drawer or ':enable-optimize="true"' in drawer or "enableOptimize" in drawer
