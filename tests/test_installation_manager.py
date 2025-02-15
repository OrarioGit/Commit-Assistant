import hashlib
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.installation_manager import InstallationManager


@pytest.fixture
def installation_manager(tmp_path: Path) -> Generator[InstallationManager, None, None]:
    """建立測試用的 InstallationManager"""
    # 建立測試用的資源目錄
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir(parents=True)

    # 使用測試用的安裝路徑
    manager = InstallationManager()
    manager.installations_path = resources_dir / ProjectInfo.INSTALLATIONS_FILE
    yield manager


def test_normalize_path(installation_manager: InstallationManager, tmp_path: Path) -> None:
    """測試路徑正規化"""
    test_path = tmp_path / "test" / "path"
    normalized = installation_manager._normalize_path(test_path)

    # 確保使用正斜線
    assert "\\" not in normalized
    assert normalized == str(test_path.resolve()).replace("\\", "/")


def test_generate_installation_id(installation_manager: InstallationManager, tmp_path: Path) -> None:
    """測試生成安裝的 ID"""
    test_path = tmp_path / "test_repo"
    normalized_path = installation_manager._normalize_path(test_path)
    expected_id = hashlib.md5(normalized_path.encode()).hexdigest()

    actual_id = installation_manager._generate_installation_id(test_path)
    assert actual_id == expected_id


def test_add_installation(installation_manager: InstallationManager, tmp_path: Path) -> None:
    """測試新增安裝記錄"""
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()

    installation_manager.add_installation(test_repo)

    # 檢查檔案是否被創建
    assert installation_manager.installations_path.exists()

    # 檢查安裝記錄
    installation = installation_manager.get_installation(test_repo)
    assert installation["repo_path"] == installation_manager._normalize_path(test_repo)
    assert installation["version"] == ProjectInfo.VERSION
    assert "installed_at" in installation
    assert "last_updated_at" in installation


def test_get_all_installations(installation_manager: InstallationManager, tmp_path: Path) -> None:
    """測試獲取所有安裝記錄"""
    # 建立測試用的repo
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()

    installation_manager.add_installation(repo1)
    installation_manager.add_installation(repo2)

    installations = installation_manager.get_all_installations()

    assert len(installations) == 2
    assert any(
        install_info["repo_path"] == installation_manager._normalize_path(repo1)
        for install_info in installations
    )
    assert any(
        install_info["repo_path"] == installation_manager._normalize_path(repo2)
        for install_info in installations
    )


def test_remove_installation(installation_manager: InstallationManager, tmp_path: Path) -> None:
    """測試移除安裝記錄"""
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()

    installation_manager.add_installation(test_repo)
    assert installation_manager.get_installation(test_repo)

    installation_manager.remove_installation(test_repo)
    assert not installation_manager.get_installation(test_repo)


def test_get_all_installations_with_missing_path(
    installation_manager: InstallationManager, tmp_path: Path
) -> None:
    """測試獲取安裝記錄時處理不存在的路徑"""
    # 建立一個臨時資料夾並記錄安裝
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    installation_manager.add_installation(test_repo)

    # 刪除該資料夾
    test_repo.rmdir()

    # 獲取安裝記錄，應該忽略不存在的路徑
    installations = installation_manager.get_all_installations()
    assert len(installations) == 0


def test_read_installations_with_invalid_file(
    installation_manager: InstallationManager, tmp_path: Path
) -> None:
    """測試讀取無效的安裝記錄檔案"""
    # 寫入無效的 TOML 內容
    installation_manager.installations_path.write_text("invalid toml content")

    installations = installation_manager._read_installations()
    assert installations == {}


def test_save_installations_error(
    installation_manager: InstallationManager, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """測試寫入安裝記錄時的錯誤處理"""

    # 模擬寫入檔案時發生錯誤
    with patch("pathlib.Path.write_text", side_effect=Exception("Mock write error")):
        # 執行儲存操作
        installation_manager._save_installations({})

        # 驗證錯誤訊息
        console_output = capsys.readouterr().out
        assert "儲存配置文件時發生錯誤" in console_output
        assert "Mock write error" in console_output
