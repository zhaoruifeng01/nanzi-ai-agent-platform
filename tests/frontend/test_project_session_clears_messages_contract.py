"""Contract: 新建项目会话须清空当前对话并换新 conversation。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EMBED = ROOT / "frontend" / "src" / "views" / "EmbedChat.vue"


def test_project_session_clears_messages_like_new_session():
    text = EMBED.read_text(encoding="utf-8")
    assert 'case "/project":' in text
    # 必须清空消息，不能只换 conversation_id
    idx = text.find('case "/project":')
    assert idx > 0
    chunk = text[idx : idx + 600]
    assert "messages.value = []" in chunk
    assert "generateNewConversation()" in chunk
    assert "openResourceScopeModal()" in chunk
    assert "CONVERSATION_CHANGED" in chunk
