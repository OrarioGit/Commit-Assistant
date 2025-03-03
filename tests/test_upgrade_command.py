import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from commit_assistant.commands.upgrade import _upgrade, check, upgrade

upgrade_module = sys.modules["commit_assistant.commands.upgrade"]


@pytest.fixture
def mock_version_data() -> dict[str, str]:
    new_version = "v1.0.0"
    current_version = "v0.0.0"
    return {"new_version": new_version, "current_version": current_version}


@patch.object(upgrade_module, "UpgradeChecker")
def test_check_has_update(mock_checker_class: MagicMock, mock_version_data: dict) -> None:
    """測試檢查是否有新版本"""
    # Setup mock
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = mock_version_data.get("new_version")
    mock_checker_class.return_value = mock_checker

    runner = CliRunner()
    result = runner.invoke(check)

    # 驗證結果
    assert result.exit_code == 0
    mock_checker.check_for_updates_version.assert_called_once()
    # 驗證是否有正確印出更新訊息
    mock_checker.print_update_message.assert_called_once_with(mock_version_data.get("new_version"))


@patch.object(upgrade_module, "UpgradeChecker")
@patch("commit_assistant.core.project_config.ProjectInfo.VERSION", new_callable=lambda: "v1.0.0")
def test_check_no_update(mock_version: str, mock_checker_class: MagicMock) -> None:
    """測試當前已經是最新版本"""
    # Setup mock
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = None
    mock_checker_class.return_value = mock_checker

    with patch("commit_assistant.utils.console_utils.console.print") as mock_print:
        runner = CliRunner()
        result = runner.invoke(check)

        # 驗證結果
        assert result.exit_code == 0
        mock_checker.check_for_updates_version.assert_called_once()
        mock_checker.print_update_message.assert_not_called()
        mock_print.assert_called_once()
        assert "目前已是最新版本" in mock_print.call_args[0][0]
        assert mock_version in mock_print.call_args[0][0]


@patch.object(upgrade_module, "_upgrade")
def test_upgrade_command_no_subcommand(mock_upgrade: MagicMock) -> None:
    """測試執行 upgrade 指令"""
    runner = CliRunner()
    result = runner.invoke(upgrade)

    # 驗證結果
    assert result.exit_code == 0
    mock_upgrade.assert_called_once_with(False)


@patch.object(upgrade_module, "upgrade")
def test_upgrade_with_subcommand(mock_upgrade: MagicMock) -> None:
    """測試執行 upgrade 指令並帶上子命令"""
    runner = CliRunner()
    result = runner.invoke(upgrade, ["check"])

    # 這裡有帶上子命令，所以不應該執行_upgrade函數
    mock_upgrade.assert_not_called()
    assert result.exit_code == 0


@patch.object(upgrade_module, "_upgrade")
def test_upgrade_command_with_yes_flag(mock_upgrade: MagicMock) -> None:
    """測試執行 upgrade 指令並帶上 --yes 參數"""
    runner = CliRunner()
    result = runner.invoke(upgrade, ["--yes"])

    # 驗證結果
    assert result.exit_code == 0
    mock_upgrade.assert_called_once_with(True)


@patch.object(upgrade_module, "UpgradeChecker")
@patch("commit_assistant.core.project_config.ProjectInfo.VERSION", new_callable=lambda: "v1.0.0")
def test_upgrade_function_no_update_available(mock_version: str, mock_checker_class: MagicMock) -> None:
    """測試更新指令，但沒有新版本可用"""
    # Setup mock
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = None
    mock_checker_class.return_value = mock_checker

    # Run function
    with patch("commit_assistant.utils.console_utils.console.print") as mock_print:
        _upgrade(True)

        # Check results
        mock_checker.check_for_updates_version.assert_called_once()
        mock_print.assert_called_once()
        assert "目前已是最新版本" in mock_print.call_args[0][0]
        assert mock_version in mock_print.call_args[0][0]


@patch.object(upgrade_module, "UpgradeChecker")
@patch("click.confirm", return_value=False)
def test_upgrade_function_user_cancels(
    mock_confirm: MagicMock, mock_checker_class: MagicMock, mock_version_data: dict
) -> None:
    """測試更新指令，但使用者取消更新"""
    # Setup mock
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = mock_version_data.get("new_version")
    mock_checker_class.return_value = mock_checker

    with patch("commit_assistant.utils.console_utils.console.print") as mock_print:
        _upgrade(False)

        # Check results
        mock_checker.check_for_updates_version.assert_called_once()
        mock_confirm.assert_called_once()
        assert mock_print.call_count == 2
        assert "已取消更新" in mock_print.call_args_list[1][0][0]


@patch.object(upgrade_module, "UpgradeChecker")
@patch.object(upgrade_module, "CommandRunner")
def test_upgrade_function_successful_update(
    mock_runner_class: MagicMock,
    mock_checker_class: MagicMock,
    mock_version_data: dict,
) -> None:
    """測試更新指令，並成功更新"""
    # Setup mocks
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = mock_version_data.get("new_version")
    mock_checker_class.return_value = mock_checker

    mock_runner = MagicMock()
    mock_runner_class.return_value = mock_runner

    # 測試--yes參數 = true的情況
    with patch("commit_assistant.utils.console_utils.console.print") as mock_print:
        _upgrade(True)

        # Check results
        mock_checker.check_for_updates_version.assert_called_once()
        mock_runner.run_command.assert_called_once()
        assert mock_print.call_count == 3
        assert "正在更新至" in mock_print.call_args_list[0][0][0]
        assert "更新成功" in mock_print.call_args_list[1][0][0]


@patch.object(upgrade_module, "UpgradeChecker")
@patch.object(upgrade_module, "CommandRunner")
def test_upgrade_function_update_error(
    mock_runner_class: MagicMock,
    mock_checker_class: MagicMock,
    mock_version_data: dict,
) -> None:
    """測試更新指令，但更新過程中發生錯誤"""
    # Setup mocks
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = mock_version_data.get("new_version")
    mock_checker_class.return_value = mock_checker

    mock_runner = MagicMock()
    # 測試發生錯誤的情況
    mock_runner.run_command.side_effect = Exception("Installation failed")
    mock_runner_class.return_value = mock_runner

    # 測試--yes參數 = true的情況
    with patch("commit_assistant.utils.console_utils.console.print") as mock_print:
        _upgrade(True)

        # Check results
        mock_checker.check_for_updates_version.assert_called_once()
        mock_runner.run_command.assert_called_once()
        assert "更新過程中發生錯誤" in mock_print.call_args[0][0]


@patch.object(upgrade_module, "UpgradeChecker")
@patch("click.confirm", return_value=True)
@patch.object(upgrade_module, "CommandRunner")
def test_upgrade_function_manual_confirm(
    mock_runner_class: MagicMock,
    mock_confirm: MagicMock,
    mock_checker_class: MagicMock,
    mock_version_data: dict,
) -> None:
    """測試更新指令，並手動確認更新"""
    # Setup mocks
    mock_checker = MagicMock()
    mock_checker.check_for_updates_version.return_value = mock_version_data.get("new_version")
    mock_checker_class.return_value = mock_checker

    mock_runner = MagicMock()
    mock_runner_class.return_value = mock_runner

    # false 代表使用者需要自己確認是否更新
    _upgrade(False)

    # Check results
    mock_confirm.assert_called_once()
    mock_runner.run_command.assert_called_once()
