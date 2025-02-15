import sys
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from commit_assistant.commands.update import update

# 取得最原始的update Module
# 而不是被Click 裝飾器包裹後的Module(會失去原本的屬性，導致無法mock)
update_module = sys.modules["commit_assistant.commands.update"]


@pytest.fixture
def mock_installation_manager() -> Generator[Mock, None, None]:
    """模擬 InstallationManager"""
    with patch.object(update_module, "InstallationManager") as mock:
        instance = mock.return_value
        instance.get_all_installations.return_value = [
            {"repo_path": "test_repo_path"},
            {"repo_path": "test_repo_path2"},
        ]
        instance.add_installation.return_value = None
        yield instance


@pytest.fixture
def mock_update_manager() -> Generator[Mock, None, None]:
    """模擬 UpdateManager"""
    with patch.object(update_module, "UpdateManager") as mock:
        instance = mock.return_value
        instance.update.return_value = None
        yield instance


def test_update_command_single_update(
    mock_installation_manager: Mock, mock_update_manager: Mock, tmp_path: Path
) -> None:
    """測試更新單一專案"""
    runner = CliRunner()
    result = runner.invoke(update, ["--repo-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "開始更新專案底下的相關檔案..." in result.output
    assert "專案底下的相關檔案更新完成!!" in result.output
    # 檢查 update 方法是否被呼叫
    mock_update_manager.update.assert_called_once()

    # 檢查 add_installation 方法被正確呼叫
    mock_installation_manager.add_installation.assert_called_once_with(Path(str(tmp_path)))


def test_update_command_single_update_error(
    mock_installation_manager: Mock, mock_update_manager: Mock, tmp_path: Path
) -> None:
    """測試更新單一專案，發生錯誤"""
    runner = CliRunner()

    with patch.object(update_module, "_update", side_effect=Exception("Test Error")):
        result = runner.invoke(update, ["--repo-path", str(tmp_path)])

    assert result.exit_code == 1
    assert "更新失敗，錯誤: " in result.output
    assert "Test Error" in result.output


def test_update_command_all_update(
    mock_installation_manager: Mock, mock_update_manager: Mock, tmp_path: Path
) -> None:
    """測試更新所有專案"""
    runner = CliRunner()
    result = runner.invoke(update, ["--repo-path", str(tmp_path), "--all-repo"])

    assert result.exit_code == 0
    assert "開始更新所有專案底下的相關檔案..." in result.output
    assert "找到 2 個已安裝的專案" in result.output  # 2 個是由mock_installation_manager 中定義
    assert "所有專案底下的相關檔案更新完成!!" in result.output
    # 檢查 update 方法是否被呼叫兩次
    assert mock_update_manager.update.call_count == 2

    # 檢查 add_installation 方法被正確呼叫
    assert mock_installation_manager.add_installation.call_count == 2


def test_update_command_all_update_with_no_installations(
    mock_installation_manager: Mock, mock_update_manager: Mock, tmp_path: Path
) -> None:
    """測試更新所有專案，但沒有任何專案被安裝"""
    runner = CliRunner()
    mock_installation_manager.get_all_installations.return_value = []  # 模擬沒有任何專案需要更新

    result = runner.invoke(update, ["--repo-path", str(tmp_path), "--all-repo"])

    assert result.exit_code == 0
    assert "沒有找到任何已安裝的專案" in result.output


def test_update_command_all_update_error(
    mock_installation_manager: Mock, mock_update_manager: Mock, tmp_path: Path
) -> None:
    """測試更新所有專案，發生錯誤"""
    runner = CliRunner()

    mock_update_manager.update.side_effect = [Exception("Test Error"), None]

    result = runner.invoke(update, ["--repo-path", str(tmp_path), "--all-repo"])

    assert result.exit_code == 0  # 部分失敗，但不影響整體執行結果
    assert "更新失敗" in result.output
    assert "Test Error" in result.output

    # 檢查 update 方法是否被呼叫兩次
    assert mock_update_manager.update.call_count == 2

    # 檢查 add_installation 方法被正確呼叫，第一次失敗，第二次成功所以只能呼叫一次
    assert mock_installation_manager.add_installation.call_count == 1
