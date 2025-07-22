import os
from pathlib import Path
from typing import Generator
from unittest.mock import mock_open, patch

import pytest
from click.testing import CliRunner

from commit_assistant.commands.config import clear, get_api_key, setup, show
from commit_assistant.enums.config_key import ConfigKey


@pytest.fixture
def mock_env_file(tmp_path: Path) -> Path:
    """創建臨時的 .env 檔案"""
    env_file = tmp_path / ".env"
    return env_file


@pytest.fixture
def mock_package_path(tmp_path: Path) -> Generator[Path, None, None]:
    """模擬套件路徑"""
    # 攔截 ProjectPaths.PACKAGE_DIR 的屬性調用，使用臨時路徑做替代
    with patch("commit_assistant.core.paths.ProjectPaths.PACKAGE_DIR", tmp_path):
        yield tmp_path


def test_setup_command(mock_package_path: Path) -> None:
    """測試 setup 命令"""
    runner = CliRunner()
    result = runner.invoke(setup, input="test-api-key\n")

    # 檢查命令是否成功執行
    assert result.exit_code == 0

    # 檢查 .env 檔案是否被正確創建
    env_file = mock_package_path / ".env"
    assert env_file.exists()

    # 檢查 API key 是否被正確寫入
    content = env_file.read_text()
    assert f"{ConfigKey.GEMINI_API_KEY.value}=test-api-key" in content

    # 檢查輸出訊息
    assert "API Key 已成功保存" in result.output


def test_setup_command_permission_error(mock_package_path: Path) -> None:
    """測試 setup 命令失敗，權限問題無法寫入 .env 檔案"""
    runner = CliRunner()

    # 模擬 touch .env 時，權限問題
    with patch.object(Path, "touch", side_effect=PermissionError("Permission denied")):
        result = runner.invoke(setup, input="test-api-key\n")

        assert result.exit_code == 1
        assert "錯誤：無法保存 API Key" in result.output
        assert "Permission denied" in result.output


def test_setup_command_write_error(mock_package_path: Path) -> None:
    """測試 setup 命令失敗，寫入過程發生錯誤時的處理"""
    runner: CliRunner = CliRunner()

    # 先創建檔案避免觸發 touch()
    env_file = mock_package_path / ".env"
    env_file.touch()

    # 模擬開啟檔案時發生錯誤
    mock_open_obj = mock_open()
    mock_open_obj.side_effect = IOError("Disk full")

    with patch("builtins.open", mock_open_obj):
        result = runner.invoke(setup, input="test-api-key\n")

        assert result.exit_code == 1
        assert "錯誤：無法保存 API Key" in result.output
        assert "Disk full" in result.output


def test_show_command() -> None:
    """測試 show 命令"""
    runner = CliRunner()

    # 模擬環境變數
    with patch.dict(os.environ, {ConfigKey.GEMINI_API_KEY.value: "test-api-key-12345"}):
        result = runner.invoke(show)

        assert result.exit_code == 0
        # 檢查是否正確地將 API key 隱藏部分內容
        assert "test-********12345" in result.output


def test_show_command_no_config(mock_package_path: Path) -> None:
    """測試未配置時的 show 命令"""
    runner = CliRunner()

    # 確保環境變數不存在
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(show)

        assert result.exit_code == 0
        assert "未配置" in result.output


def test_clear_command(mock_package_path: Path) -> None:
    """測試 clear 命令"""
    runner = CliRunner()

    # 創建測試用的 .env 檔案，並先寫入一些內容
    env_file = mock_package_path / ".env"
    env_file.write_text(f"{ConfigKey.GEMINI_API_KEY.value}=test-key")

    # 測試確認刪除
    result = runner.invoke(clear, input="y\n")
    assert result.exit_code == 0
    assert not env_file.exists()
    assert "配置已清除" in result.output


def test_clear_command_and_cancel(mock_package_path: Path) -> None:
    """測試 clear 命令，但取消刪除"""
    runner = CliRunner()

    # 創建測試用的 .env 檔案，並先寫入一些內容
    env_file = mock_package_path / ".env"
    env_file.write_text(f"{ConfigKey.GEMINI_API_KEY.value}=test-key")

    # 測試取消刪除
    result = runner.invoke(clear, input="n\n")
    assert result.exit_code == 0
    assert env_file.exists()
    assert "動作已取消" in result.output


def test_clear_command_no_file(mock_package_path: Path) -> None:
    """測試當 .env 不存在時的 clear 命令"""
    runner = CliRunner()
    result = runner.invoke(clear)

    assert result.exit_code == 0
    assert "沒有找到配置文件" in result.output


def test_get_api_key(mock_package_path: Path) -> None:
    """測試 get_api_key 命令"""
    runner = CliRunner()

    # 測試有 API key 的情況
    with patch.dict(os.environ, {ConfigKey.GEMINI_API_KEY.value: "test-api-key-12345"}):
        result = runner.invoke(get_api_key)
        assert result.exit_code == 0
        assert "test-********12345" in result.output

    # 測試沒有 API key 的情況
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(get_api_key)
        assert result.exit_code == 0
        assert "API Key 未配置" in result.output
