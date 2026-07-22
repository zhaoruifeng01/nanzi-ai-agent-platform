"""Contract: 快捷指令条超出宽度时可横向滚动。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAT_INPUT = ROOT / "frontend" / "src" / "components" / "embed" / "ChatInput.vue"


def test_shortcut_row_supports_horizontal_scroll():
    text = CHAT_INPUT.read_text(encoding="utf-8")
    assert "shortcutScrollRef" in text
    assert "overflow-x-auto" in text
    assert "onShortcutWheel" in text
    assert "hasShortcutChips" in text
    # 不再用测量截断隐藏指令
    assert "recalcVisibleShortcuts" not in text
    assert "hasHiddenShortcuts" not in text
