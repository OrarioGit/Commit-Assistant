import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner
from google.generativeai.types import GenerateContentResponse

from commit_assistant.commands.summary import (
    CommitSummaryGenerator,
    _parse_date,
    summary,
)
from commit_assistant.enums.exit_code import ExitCode

summary_module = sys.modules["commit_assistant.commands.summary"]


# Fixtures
@pytest.fixture
def mock_git_runner() -> Generator[Mock, None, None]:
    """模擬 GitCommandRunner"""
    with patch.object(summary_module, "GitCommandRunner") as mock:
        instance = mock.return_value
        instance.get_commits_in_date_range.return_value = "test commit message"
        yield instance


@pytest.fixture
def mock_summary_generator() -> Generator[Mock, None, None]:
    """模擬 CommitSummaryGenerator"""
    with patch.object(summary_module, "CommitSummaryGenerator") as mock:
        instance = mock.return_value
        response = Mock(spec=GenerateContentResponse)
        response.text = "• 測試摘要\n• 測試項目二"
        instance.generate_commit_summary.return_value = response
        yield instance


# _parse_date 測試
# 先定義出要測試的參數和預期結果
@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("today", datetime.now().replace(hour=0, minute=0, second=0)),
        ("yesterday", (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0)),
        ("7d", (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0)),
        ("2024-02-14", datetime(2024, 2, 14)),
        ("2024/02/14", datetime(2024, 2, 14)),
        (None, datetime.now()),
    ],
)
def test_parse_date(date_str: str, expected: datetime) -> None:
    """測試日期解析功能"""
    result = _parse_date(date_str)

    if date_str in ["today", "yesterday", "7d", None]:
        # 對於相對日期，只比較日期部分
        assert result.date() == expected.date()
    else:
        assert result == expected


def test_parse_date_invalid_format() -> None:
    """測試無效的日期格式"""
    with pytest.raises(click.BadParameter, match="Unsupported date format"):
        _parse_date("invalid-date")


@pytest.mark.parametrize(
    "invalid_date_str",
    [
        "d",  # 沒有數字
        "ad",  # 不是數字
        "1.5d",  # 小數
    ],
)
def test_parse_date_invalid_days(invalid_date_str: str) -> None:
    """測試無效的 Nd 格式"""
    with pytest.raises(click.BadParameter, match="Unsupported date format"):
        _parse_date(invalid_date_str)


# CommitSummaryGenerator 測試
def test_generate_commit_summary() -> None:
    """測試生成摘要"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_api_key"}):
        generator = CommitSummaryGenerator()

        with patch.object(generator, "_generate_content") as mock_generate:
            mock_response = Mock(spec=GenerateContentResponse)
            mock_generate.return_value = mock_response

            start_dt = datetime(2024, 2, 14)
            end_dt = datetime(2024, 2, 15)
            commit_msg = "test commit message"

            response = generator.generate_commit_summary(commit_msg, start_dt, end_dt)

            assert response == mock_response
            mock_generate.assert_called_once()


def test_generate_commit_summary_error() -> None:
    """測試生成摘要出現錯誤"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_api_key"}):
        generator = CommitSummaryGenerator()

        with patch.object(generator, "_generate_content", side_effect=Exception("API Error")):
            start_dt = datetime(2024, 2, 14)
            end_dt = datetime(2024, 2, 15)
            response = generator.generate_commit_summary("test", start_dt, end_dt)

            assert response is None


# summary 命令測試
def test_summary_command_success(mock_git_runner: Mock, mock_summary_generator: Mock, tmp_path: Path) -> None:
    """測試摘要命令成功執行"""
    runner = CliRunner()

    with patch.object(summary_module, "pyperclip") as mock_pyperclip:
        result = runner.invoke(
            summary, ["--start-from", "2024-02-14", "--end-to", "2024-02-15", "--repo-path", str(tmp_path)]
        )

        assert result.exit_code == ExitCode.SUCCESS.value

        # 檢查是否有正確調用相關方法
        mock_git_runner.get_commits_in_date_range.assert_called_once()
        mock_summary_generator.generate_commit_summary.assert_called_once()
        mock_pyperclip.copy.assert_called_once()


def test_summary_command_no_commits(mock_git_runner: Mock, tmp_path: Path) -> None:
    """測試沒有找到 commit 的情況"""
    runner = CliRunner()
    mock_git_runner.get_commits_in_date_range.return_value = ""

    result = runner.invoke(
        summary, ["--start-from", "2024-02-14", "--end-to", "2024-02-15", "--repo-path", str(tmp_path)]
    )

    assert result.exit_code == ExitCode.CANCEL.value
    assert "沒有找到符合條件的" in result.output


def test_summary_command_no_start_date(
    mock_git_runner: Mock, mock_summary_generator: Mock, tmp_path: Path
) -> None:
    """測試沒有指定開始日期"""
    runner = CliRunner()
    with patch.object(summary_module, "pyperclip") as mock_pyperclip:
        result = runner.invoke(summary, ["--end-to", "2024-02-15", "--repo-path", str(tmp_path)])

    # 應該要能正常執行
    assert result.exit_code == ExitCode.SUCCESS.value

    # 檢查是否有正確調用相關方法
    mock_git_runner.get_commits_in_date_range.assert_called_once()
    mock_summary_generator.generate_commit_summary.assert_called_once()
    mock_pyperclip.copy.assert_called_once()


def test_summary_command_no_end_date(
    mock_git_runner: Mock, mock_summary_generator: Mock, tmp_path: Path
) -> None:
    """測試沒有指定結束日期"""
    runner = CliRunner()
    with patch.object(summary_module, "pyperclip") as mock_pyperclip:
        result = runner.invoke(summary, ["--start-from", "2024-02-14", "--repo-path", str(tmp_path)])

    # 應該要能正常執行
    assert result.exit_code == ExitCode.SUCCESS.value

    # 檢查是否有正確調用相關方法
    mock_git_runner.get_commits_in_date_range.assert_called_once()
    mock_summary_generator.generate_commit_summary.assert_called_once()
    mock_pyperclip.copy.assert_called_once()


def test_summary_command_summary_error(
    mock_git_runner: Mock, mock_summary_generator: Mock, tmp_path: Path
) -> None:
    """測試生成摘要時出現錯誤"""
    runner = CliRunner()

    # 模擬summary生成失敗，返回None
    mock_summary_generator.generate_commit_summary.return_value = None

    with patch.object(summary_module, "pyperclip") as mock_pyperclip:
        result = runner.invoke(
            summary, ["--start-from", "2024-02-14", "--end-to", "2024-02-15", "--repo-path", str(tmp_path)]
        )

        assert result.exit_code == ExitCode.ERROR.value
        assert "摘要生成失敗" in result.output
        mock_pyperclip.copy.assert_not_called()


def test_summary_command_pyperclip_error(
    mock_git_runner: Mock, mock_summary_generator: Mock, tmp_path: Path
) -> None:
    """測試複製到剪貼板時出現錯誤"""
    runner = CliRunner()

    with patch.object(summary_module, "pyperclip") as mock_pyperclip:
        mock_pyperclip.copy.side_effect = Exception("Test Error")

        result = runner.invoke(
            summary, ["--start-from", "2024-02-14", "--end-to", "2024-02-15", "--repo-path", str(tmp_path)]
        )

        # 這裡失敗會改為直接顯示摘要內容，不會返回錯誤
        assert result.exit_code == ExitCode.SUCCESS.value
        assert "無法複製摘要到剪貼簿, 請確認操作環境是否支援剪貼簿操作" in result.output
