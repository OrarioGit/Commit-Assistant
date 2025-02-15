import sys
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from commit_assistant.commands.install import install
from commit_assistant.core.project_config import ProjectInfo

install_module = sys.modules["commit_assistant.commands.install"]


@pytest.fixture
def mock_managers() -> Generator[tuple[Mock, Mock, Mock], None, None]:
    """模擬所有需要的 managers"""
    with (
        patch.object(install_module, "HookManager") as mock_hook_manager,
        patch.object(install_module, "InstallationManager") as mock_install_manager,
        patch.object(install_module, "install_config") as mock_install_config,
    ):
        # 設定 HookManager mock
        hook_instance = mock_hook_manager.return_value
        hook_instance.install_hook.return_value = None

        # 設定 InstallationManager mock
        install_instance = mock_install_manager.return_value
        install_instance.add_installation.return_value = None

        yield hook_instance, install_instance, mock_install_config


@pytest.fixture
def mock_project_paths(tmp_path: Path) -> Generator[Path, None, None]:
    """模擬專案路徑"""
    # 建立測試用的目錄結構
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir(parents=True)

    # 建立測試用的 hook 模板
    hook_template = hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME
    hook_template.write_text("test hook content")

    with patch.object(install_module, "ProjectPaths") as mock_project_paths:
        mock_project_paths.HOOKS_DIR = hooks_dir
        yield tmp_path


def test_install_command_success(
    mock_managers: tuple[Mock, Mock, Mock], mock_project_paths: Path, tmp_path: Path
) -> None:
    """測試安裝命令成功的情況"""
    hook_manager, install_manager, mock_install_config = mock_managers
    runner = CliRunner()

    # 執行安裝命令
    result = runner.invoke(install, ["--repo-path", str(tmp_path)])

    # 驗證結果
    assert result.exit_code == 0

    # 驗證各個模組被正確呼叫
    hook_manager.install_hook.assert_called_once()
    mock_install_config.assert_called_once_with(str(tmp_path))
    install_manager.add_installation.assert_called_once_with(Path(tmp_path))


def test_install_command_error_invalid_path() -> None:
    """測試安裝到無效路徑的情況"""
    runner = CliRunner()

    # 執行安裝命令，使用不存在的路徑
    result = runner.invoke(install, ["--repo-path", "/invalid/path"])

    assert result.exit_code == 2  # Click 的路徑驗證錯誤碼
    assert "Directory" in result.output  # Click 的錯誤訊息


def test_install_command_hook_error(
    mock_managers: tuple[Mock, Mock, Mock], mock_project_paths: Path, tmp_path: Path
) -> None:
    """測試安裝 hook 失敗的情況"""
    hook_manager, _, _ = mock_managers
    runner = CliRunner()

    # 模擬 hook 安裝失敗
    hook_manager.install_hook.side_effect = Exception("Hook installation failed")

    result = runner.invoke(install, ["--repo-path", str(tmp_path)])

    assert result.exit_code == 1
    assert "安裝失敗" in result.output
    assert "Hook installation failed" in result.output


def test_install_command_config_error(
    mock_managers: tuple[Mock, Mock, Mock], mock_project_paths: Path, tmp_path: Path
) -> None:
    """測試安裝 config 失敗的情況"""
    _, _, mock_install_config = mock_managers
    runner = CliRunner()

    # 模擬 config 安裝失敗
    mock_install_config.side_effect = Exception("Config installation failed")

    result = runner.invoke(install, ["--repo-path", str(tmp_path)])

    assert result.exit_code == 1
    assert "安裝失敗" in result.output
    assert "Config installation failed" in result.output
