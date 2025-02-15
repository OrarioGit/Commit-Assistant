from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
import tomli
import tomli_w

from commit_assistant.scripts.build_pyproject import update_pyproject_toml


@pytest.fixture
def mock_root_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """模擬專案根目錄"""
    with patch("commit_assistant.core.paths.ProjectPaths.ROOT_DIR", tmp_path):
        yield tmp_path


@pytest.fixture
def mock_config() -> Generator[dict, None, None]:
    """模擬生成的設定內容"""
    mock_config = {
        "project": {"name": "commit-assistant", "version": "0.1.0"},
        "tool": {"pytest": {"ini_options": {"testpaths": ["tests"]}}},
    }

    with patch("commit_assistant.scripts.build_pyproject.generate_toml_config", return_value=mock_config):
        yield mock_config


def test_update_pyproject_toml(mock_root_dir: Path, mock_config: dict) -> None:
    """測試更新 pyproject.toml"""
    update_pyproject_toml()

    # 檢查檔案是否被創建
    toml_path = mock_root_dir / "pyproject.toml"
    assert toml_path.exists()

    # 讀取並檢查內容
    with open(toml_path, "rb") as f:
        saved_config = tomli.load(f)

    assert saved_config == mock_config


def test_update_pyproject_toml_existing_file(mock_root_dir: Path, mock_config: dict) -> None:
    """測試更新已存在的 pyproject.toml"""
    # 先建立一個現有的檔案
    toml_path = mock_root_dir / "pyproject.toml"
    with open(toml_path, "wb") as f:
        tomli_w.dump({"old": "config"}, f)

    update_pyproject_toml()

    # 檢查內容是否被更新
    with open(toml_path, "rb") as f:
        saved_config = tomli.load(f)

    assert saved_config == mock_config
    assert "old" not in saved_config


def test_update_pyproject_toml_permission_error(mock_root_dir: Path, mock_config: dict) -> None:
    """測試寫入權限錯誤的情況"""
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            update_pyproject_toml()
