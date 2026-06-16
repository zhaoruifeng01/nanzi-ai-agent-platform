from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.no_infrastructure


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _assert_dataset_menu_loading_contract(source: str) -> None:
    assert "const datasetMenuLoading = ref(false);" in source
    assert "if (datasetMenuLoading.value || isProcessing.value) {" in source
    assert "datasetMenuLoading.value = true;" in source
    assert "isProcessing.value = true;" in source
    assert "datasetMenuLoading.value = false;" in source
    assert "isProcessing.value = false;" in source
    assert "case \"/dataset_menu\":" in source
    assert "let datasetMenuThoughtTimer: ReturnType<typeof setInterval> | null = null;" in source
    assert "datasetMenuThoughtTimer = setInterval(() => {" in source
    assert "navMsg.value.thoughtDuration = (" in source
    assert "clearInterval(datasetMenuThoughtTimer);" in source
    assert "datasetMenuThoughtTimer = null;" in source


def test_embed_chat_locks_input_while_dataset_menu_loads():
    _assert_dataset_menu_loading_contract(_source("frontend/src/views/EmbedChat.vue"))


def test_agent_debug_locks_input_while_dataset_menu_loads():
    _assert_dataset_menu_loading_contract(_source("frontend/src/views/AgentDebug.vue"))
