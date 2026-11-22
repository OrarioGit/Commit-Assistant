from unittest.mock import patch

import pytest
from rich.console import Console

from commit_assistant.core.commit_suggestion import CommitSuggestion, CommitWarning, WarningLevel
from commit_assistant.utils import console_utils


@pytest.fixture
def record_console() -> Console:
    """以不輸出到終端機的 console 取代全域 console，方便檢查輸出內容"""
    test_console = Console(record=True, width=100, force_terminal=False)
    with patch.object(console_utils, "console", test_console):
        yield test_console


def test_display_commit_suggestion_with_warnings_and_notes(record_console: Console) -> None:
    """測試顯示 commit message、注意事項與補充說明"""
    suggestion = CommitSuggestion(
        message="feat: add login\n\nbody",
        notes="選用 feat 因為是新功能",
        warnings=[
            CommitWarning(level=WarningLevel.HIGH, message="疑似寫死 API key"),
            CommitWarning(level=WarningLevel.MEDIUM, message="殘留 print"),
            CommitWarning(level=WarningLevel.LOW, message="缺少測試"),
        ],
    )

    console_utils.display_commit_suggestion(suggestion)
    output = record_console.export_text()

    assert "feat: add login" in output
    assert "注意事項" in output
    assert "✗ 高" in output and "疑似寫死 API key" in output
    assert "! 中" in output and "殘留 print" in output
    assert "· 低" in output and "缺少測試" in output
    assert "補充說明" in output and "選用 feat 因為是新功能" in output


def test_display_commit_suggestion_message_only(record_console: Console) -> None:
    """測試沒有注意事項與補充說明時，只顯示 commit message"""
    console_utils.display_commit_suggestion(CommitSuggestion(message="fix: bug"))
    output = record_console.export_text()

    assert "fix: bug" in output
    assert "注意事項" not in output
    assert "補充說明" not in output
