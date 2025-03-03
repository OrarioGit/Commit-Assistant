import sys
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from commit_assistant.cli import cli
from commit_assistant.core.project_config import ProjectInfo

cli_module = sys.modules["commit_assistant.cli"]


def test_cli_version() -> None:
    """測試顯示版本資訊"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    # 檢查是否有成功執行
    assert result.exit_code == 0
    # 檢查是否顯示了正確的版本資訊
    assert ProjectInfo.VERSION in result.output
    assert ProjectInfo.NAME in result.output


def test_cli_help() -> None:
    """測試CLI help指令"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    # 檢查是否有成功執行
    assert result.exit_code == 0
    # 檢查是否有顯示help訊息
    assert "Commit Assistant CLI 工具" in result.output
    # 檢查是否有顯示我們所有的子命令
    assert "commit" in result.output
    assert "install" in result.output
    assert "config" in result.output
    assert "summary" in result.output
    assert "update" in result.output


def test_cli_without_command() -> None:
    """測試沒有指定子命令時的行為"""
    runner = CliRunner()
    result = runner.invoke(cli)

    # 應該顯示幫助訊息而不是錯誤
    assert result.exit_code == 0
    assert "Commit Assistant CLI 工具" in result.output


@patch.object(cli_module, "UpgradeChecker")
def test_upgrade_check_on_commands(mock_upgrade_checker: MagicMock) -> None:
    """測試非upgrade命令會觸發版本檢查"""
    mock_checker_instance = MagicMock()
    mock_upgrade_checker.return_value = mock_checker_instance

    runner = CliRunner()
    # 測試隨便一個非upgrade的命令
    runner.invoke(cli, ["commit", "--help"])

    # 驗證UpgradeChecker被初始化並執行了檢查
    mock_upgrade_checker.assert_called_once()
    mock_checker_instance.run_version_check.assert_called_once()


@patch.object(cli_module, "UpgradeChecker")
def test_upgrade_check_on_upgrade_command(mock_upgrade_checker: MagicMock) -> None:
    """測試upgrade命令不會觸發版本檢查"""
    mock_checker_instance = MagicMock()
    mock_upgrade_checker.return_value = mock_checker_instance

    runner = CliRunner()
    # 測試upgrade命令
    runner.invoke(cli, ["upgrade", "--help"])

    # 驗證UpgradeChecker沒有執行檢查
    mock_upgrade_checker.assert_not_called()
