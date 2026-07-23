"""Contract: ConfirmModal 须 Teleport 到 body，且层级高于指令库弹层。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODAL = ROOT / "frontend" / "src" / "components" / "ConfirmModal.vue"
EMBED = ROOT / "frontend" / "src" / "views" / "EmbedChat.vue"
CHAT_INPUT = ROOT / "frontend" / "src" / "components" / "embed" / "ChatInput.vue"


def test_confirm_modal_teleports_above_command_drawer():
    modal = MODAL.read_text(encoding="utf-8")
    assert 'Teleport to="body"' in modal or "Teleport to='body'" in modal
    assert "z-[13000]" in modal

    embed = EMBED.read_text(encoding="utf-8")
    # 禁止再把确认框压到指令库下面
    assert 'style="z-index: 200;"' not in embed

    drawer = CHAT_INPUT.read_text(encoding="utf-8")
    assert "z-[1200]" in drawer
