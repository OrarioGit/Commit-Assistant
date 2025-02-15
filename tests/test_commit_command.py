import sys
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from google.generativeai.types import GenerateContentResponse

from commit_assistant.commands.commit import (
    EnhancedCommitGenerator,
    ExitCode,
    UserChoices,
    commit,
    edit_commit_message,
    get_user_choice,
)
from commit_assistant.enums.config_key import ConfigKey

# 取得最原始的commit Module
# 而不是被Click 裝飾器包裹後的Module(會失去原本的屬性，導致無法mock)
commit_module = sys.modules["commit_assistant.commands.commit"]


@pytest.fixture
def mock_git_runner() -> Generator[Mock, None, None]:
    """模擬 GitCommandRunner"""
    with patch.object(commit_module, "GitCommandRunner") as mock:
        runner = mock.return_value
        runner.get_staged_files.return_value = ["file1.py", "file2.py"]
        runner.get_staged_diff.return_value = "mock diff content"
        yield runner


@pytest.fixture
def mock_generator() -> Generator[Mock, None, None]:
    """模擬 EnhancedCommitGenerator"""
    with patch.object(commit_module, "EnhancedCommitGenerator") as mock:
        instance = mock.return_value
        response = Mock(spec=GenerateContentResponse)
        response.text = "feat: test commit message"
        instance.generate_structured_message.return_value = response
        yield instance


# EnhancedCommitGenerator 測試
def test_generate_structured_message() -> None:
    """測試生成結構化的 commit message"""
    # 先往環境裡加入 API_KEY，讓 EnhancedCommitGenerator 可以正常初始化
    with patch.dict("os.environ", {ConfigKey.GEMINI_API_KEY.value: "test_api_key"}):
        generator = EnhancedCommitGenerator()

    # Mock generator裡面的 _generate_content 方法
    with patch.object(generator, "_generate_content") as mock_generate:
        mock_response = Mock(spec=GenerateContentResponse)
        mock_generate.return_value = mock_response

        # 模擬要測試的參數
        files = ["test.py"]
        diff = "test diff"

        with patch.dict("os.environ", {"COMMIT_STYLE": "custom"}):
            response = generator.generate_structured_message(files, diff)

        assert response == mock_response
        mock_generate.assert_called_once()


def test_generate_structured_message_error() -> None:
    """測試生成結構化的 commit message 出現錯誤"""
    # 先往環境裡加入 API_KEY，讓 EnhancedCommitGenerator 可以正常初始化
    with patch.dict("os.environ", {ConfigKey.GEMINI_API_KEY.value: "test_api_key"}):
        generator = EnhancedCommitGenerator()

    # Mock generator裡面的 _generate_content 方法
    with patch.object(generator, "_generate_content") as mock_generate:
        mock_generate.side_effect = Exception("mock error")

        # 模擬要測試的參數
        files = ["test.py"]
        diff = "test diff"

        with patch.dict("os.environ", {"COMMIT_STYLE": "custom"}):
            response = generator.generate_structured_message(files, diff)

        assert response is None


# get_user_choice 測試
def test_get_user_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試取得使用者選擇"""
    choices = [
        UserChoices.USE_AI_MESSAGE.value,
        UserChoices.EDIT_AI_MESSAGE.value,
        UserChoices.CANCEL_OPERATION.value,
    ]

    # 模擬使用者輸入2
    monkeypatch.setattr("builtins.input", lambda _: "2")

    user_choice = get_user_choice(choices)

    assert user_choice == UserChoices.EDIT_AI_MESSAGE.value


def test_get_user_choice_invalid_then_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試使用者先輸入無效選項後再輸入有效選項"""
    choices = [
        UserChoices.USE_AI_MESSAGE.value,
        UserChoices.EDIT_AI_MESSAGE.value,
        UserChoices.CANCEL_OPERATION.value,
    ]

    inputs = iter(["0", "abc", "1"])  # 先輸入無效選項，最後輸入有效選項1
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    user_choice = get_user_choice(choices)

    assert user_choice == UserChoices.USE_AI_MESSAGE.value


# commit 命令測試
def test_commit_command_success(mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path) -> None:
    """測試 commit 命令成功"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬使用者選擇直接使用 AI 訊息
    with patch.object(commit_module, "get_user_choice", return_value=UserChoices.USE_AI_MESSAGE.value):
        result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.SUCCESS.value
    assert msg_file.read_text() == "feat: test commit message"


def test_commit_command_no_staged_files(mock_git_runner: Mock, tmp_path: Path) -> None:
    """測試git stage沒有任何檔案的情況"""
    mock_git_runner.get_staged_files.return_value = []

    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()
    result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.CANCEL.value
    assert "沒有發現暫存的變更" in result.output


def test_commit_command_user_cancel(mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path) -> None:
    """測試使用者直接Ctrl+C取消操作"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬使用者直接Ctrl+C取消操作
    mock_generator.generate_structured_message.side_effect = KeyboardInterrupt
    result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.CANCEL.value
    assert "操作已取消" in result.output


def test_commit_command_error(mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path) -> None:
    """測試執行commit 指令的時候發生錯誤"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬生成commit message時發生錯誤
    mock_generator.generate_structured_message.side_effect = Exception("mock error")
    result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.ERROR
    assert "錯誤：" in result.output
    assert "mock error" in result.output


def test_commit_command_generate_error(mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path) -> None:
    """測試生成commit message時發生錯誤"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬生成commit message時發生錯誤(返回None)
    mock_generator.generate_structured_message.return_value = None
    result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.ERROR
    assert "✗ 生成 commit message 失敗" in result.output


def test_commit_command_not_enable(tmp_path: Path) -> None:
    """測試設定中不啟用commit assistant"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬設定中不啟用commit assistant
    with patch.dict("os.environ", {"ENABLE_COMMIT_ASSISTANT": "false"}):
        result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.SUCCESS.value


def test_commit_command_user_cancel_update_commit_message(
    mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path
) -> None:
    """測試使用者在更新message檔案時，選擇取消作業"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬使用者選擇取消
    with patch.object(commit_module, "get_user_choice", return_value=UserChoices.CANCEL_OPERATION.value):
        result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.CANCEL.value
    assert "Commit 已取消" in result.output


def test_commit_command_user_update_commit_message_error(
    mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path
) -> None:
    """測試使用者在更新message檔案時，發生錯誤"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬get_user_choice 函數發生錯誤
    with patch.object(commit_module, "get_user_choice", side_effect=Exception("mock error")):
        result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.ERROR
    assert "錯誤：" in result.output


def test_commit_command_user_edit_update_commit_message(
    mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path
) -> None:
    """測試使用者在更新message檔案時，選擇編輯作業"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬使用者選擇編輯
    with patch.object(commit_module, "get_user_choice", return_value=UserChoices.EDIT_AI_MESSAGE.value):
        # 模擬使用者編輯內容後，確認作業
        with patch.object(commit_module, "edit_commit_message", return_value=("edited message", True)):
            result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.SUCCESS.value
    assert "edited message" in msg_file.read_text()  # 更新內容要確實寫入檔案


def test_commit_command_user_cancel_edit_update_commit_message(
    mock_git_runner: Mock, mock_generator: Mock, tmp_path: Path
) -> None:
    """測試使用者在更新message檔案時，選擇編輯作業時取消"""
    msg_file = tmp_path / "COMMIT_MSG"
    msg_file.touch()

    runner = CliRunner()

    # 模擬使用者選擇編輯
    with patch.object(commit_module, "get_user_choice", return_value=UserChoices.EDIT_AI_MESSAGE.value):
        # 模擬使用者開始編輯後，取消作業
        # False 代表使用者取消
        with patch.object(commit_module, "edit_commit_message", return_value=("", False)):
            result = runner.invoke(commit, ["--msg-file", str(msg_file), "--repo-path", str(tmp_path)])

    assert result.exit_code == ExitCode.CANCEL.value


def test_edit_commit_message_confirm_save() -> None:
    """測試編輯 commit message 並確認儲存"""
    # 模擬使用者輸入新的 message 並確認
    with patch("questionary.text") as mock_text, patch("questionary.confirm") as mock_confirm:
        # 模擬 questionary.text().ask() 返回編輯後的訊息
        mock_text.return_value.ask.return_value = "feat: edited message"
        # 模擬 questionary.confirm().ask() 返回 True
        mock_confirm.return_value.ask.return_value = True

        message, confirmed = edit_commit_message("initial message")

        assert message == "feat: edited message"
        assert confirmed is True
        # 確認 text 被正確呼叫
        mock_text.assert_called_once_with(
            "請輸入/編輯 commit message：", default="initial message", multiline=True
        )


def test_edit_commit_message_cancel_by_ctrl_c() -> None:
    """測試按 Ctrl+C 取消編輯"""
    with patch("questionary.text") as mock_text:
        # 模擬按 Ctrl+C (返回 None)
        mock_text.return_value.ask.return_value = None

        message, confirmed = edit_commit_message("initial message")

        assert message == ""
        assert confirmed is False


def test_edit_commit_message_retry_then_confirm() -> None:
    """測試先取消後確認的情況"""
    with patch("questionary.text") as mock_text, patch("questionary.confirm") as mock_confirm:
        # 設定連續的回應：第一次輸入後不確認，第二次輸入後確認
        mock_text.return_value.ask.side_effect = ["first try message", "second try message"]
        mock_confirm.return_value.ask.side_effect = [False, True]

        message, confirmed = edit_commit_message("initial message")

        assert message == "second try message"
        assert confirmed is True
        # 確認 text 被呼叫了兩次
        assert mock_text.call_count == 2
