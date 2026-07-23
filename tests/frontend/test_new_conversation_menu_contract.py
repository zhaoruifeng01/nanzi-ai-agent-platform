"""Contract: 新会话类型菜单不应因 mouseleave / 空隙误关；且不被快捷指令横向滚动裁切。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAT_INPUT = ROOT / "frontend" / "src" / "components" / "embed" / "ChatInput.vue"


def test_new_conversation_menu_stays_open_until_click_outside():
    text = CHAT_INPUT.read_text(encoding="utf-8")
    assert "showNewConversationMenu" in text
    assert "newConversationMenuRef" in text
    assert "setNewConversationMenuRef" in text
    assert "新建项目会话" in text
    assert "selectNewConversationType('/project')" in text
    # 点击打开：禁止用 mouseleave 关菜单（空隙会导致来不及点第二项）
    assert '@mouseleave="showNewConversationMenu = false"' not in text
    assert "newConversationMenuPanelRef" in text
    assert "getNewConversationTriggerEl" in text
    assert "Teleport to=\"body\"" in text or "Teleport to='body'" in text
    # 菜单用 fixed 挂到 body，避免 overflow-x-auto 裁切
    assert "newConversationMenuPosition" in text
    assert "updateNewConversationMenuPosition" in text


def test_new_conversation_menu_closes_on_escape():
    text = CHAT_INPUT.read_text(encoding="utf-8")
    assert "if (showNewConversationMenu.value)" in text
