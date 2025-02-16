import os
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import patch

import pytest

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import CommitStyle
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.utils.config_utils import (
    _load_config_from_config_file,
    install_config,
    load_config,
)


@pytest.fixture
def mock_project_paths(tmp_path: Path) -> Generator[Path, None, None]:
    """模擬專案路徑"""
    # 建立測試用的目錄結構
    package_dir = tmp_path / "package"
    resources_dir = package_dir / "resources"
    config_dir = resources_dir / "config"
    config_dir.mkdir(parents=True)

    # 建立測試用的設定檔
    config_file = config_dir / ".commit-assistant-config"
    config_file.write_text(
        """
        # test config
        COMMIT_STYLE=custom
        ENABLE_COMMIT_ASSISTANT=true
    """,
        encoding="utf-8",
    )

    with (
        patch("commit_assistant.core.paths.ProjectPaths.PACKAGE_DIR", package_dir),
        patch("commit_assistant.core.paths.ProjectPaths.CONFIG_DIR", config_dir),
    ):
        yield tmp_path


def test_load_config_from_config_file(tmp_path: Path) -> None:
    """測試從設定檔載入設定"""
    # 建立測試用的設定檔
    config_dir = tmp_path / ".commit-assistant"
    config_dir.mkdir()
    config_file = config_dir / ".commit-assistant-config"
    config_file.write_text(
        """
            # 這是註解
            COMMIT_STYLE=emoji
            USE_MODEL=test-model
        """,
        encoding="utf-8",
    )

    config: Dict[str, Any] = {}
    _load_config_from_config_file(config, str(tmp_path))

    assert config["COMMIT_STYLE"] == "emoji"
    assert config["USE_MODEL"] == "test-model"
    assert "#" not in str(config)  # 確認註解沒有被載入


def test_load_config_from_env(tmp_path: Path) -> None:
    """測試從環境變數載入設定"""
    # 建立測試用的 .env 檔案
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
        GEMINI_API_KEY=test-key
        COMMIT_STYLE=conventional
        """,
        encoding="utf-8",
    )
    with patch("commit_assistant.core.paths.ProjectPaths.PACKAGE_DIR", tmp_path):
        # 清空環境變數
        with patch.dict(os.environ, {}, clear=True):
            load_config(str(tmp_path))

            assert os.environ["GEMINI_API_KEY"] == "test-key"
            assert os.environ["COMMIT_STYLE"] == "conventional"


def test_load_config_default_values(tmp_path: Path) -> None:
    """測試載入預設值"""
    with patch.dict(os.environ, {}, clear=True):  # 清空環境變數
        load_config(str(tmp_path))

        assert os.environ[ConfigKey.ENABLE_COMMIT_ASSISTANT.value] == "True"
        assert os.environ[ConfigKey.USE_MODEL.value] == "gemini-2.0-flash-exp"
        assert os.environ[ConfigKey.COMMIT_STYLE.value] == CommitStyle.CONVENTIONAL.value


def test_load_config_priority(tmp_path: Path) -> None:
    """測試設定的優先順序"""
    # 建立 .env 檔案
    env_file = tmp_path / ".env"
    env_file.write_text("COMMIT_STYLE=conventional\n")

    # 建立專案設定檔
    config_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir()
    config_file = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME
    config_file.write_text("COMMIT_STYLE=emoji\n", encoding="utf-8")

    with patch("commit_assistant.core.paths.ProjectPaths.PACKAGE_DIR", tmp_path):
        load_config(str(tmp_path))

        # 應該使用專案設定檔的值（優先順序最高）
        assert os.environ["COMMIT_STYLE"] == "emoji"


def test_install_config(tmp_path: Path, mock_project_paths: Path) -> None:
    """測試安裝設定檔"""
    # 執行安裝
    install_config(str(tmp_path))

    # 確認設定檔被複製
    config_file = tmp_path / ProjectInfo.CONFIG_TEMPLATE_NAME
    assert config_file.exists()
    assert "COMMIT_STYLE" in config_file.read_text()


def test_install_config_copy_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """測試安裝設定檔時發生錯誤"""
    # 模擬複製檔案時發生錯誤
    with patch("shutil.copyfile", side_effect=Exception("Mock copy error")):
        install_config(str(tmp_path))

        # 驗證錯誤訊息
        console_output = capsys.readouterr().out
        assert "安裝配置文件失敗" in console_output


def test_install_config_existing_file(tmp_path: Path) -> None:
    """測試安裝設定檔到已存在檔案的情況"""
    # 建立已存在的設定檔
    config_file = tmp_path / ProjectInfo.CONFIG_TEMPLATE_NAME
    original_content = "COMMIT_STYLE=custom"
    config_file.write_text(original_content)

    # 執行安裝
    install_config(str(tmp_path))

    # 確認原檔案未被覆蓋
    assert config_file.read_text() == original_content


def test_load_config_file_error(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """測試載入設定檔出錯的情況"""
    config_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir()
    config_file = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME
    config_file.write_text("invalid=config=format")  # 無效的格式

    # 模擬載入設定檔時出錯
    with patch("commit_assistant.utils.config_utils._load_config_from_config_file", side_effect=Exception):
        load_config(str(tmp_path))

        # 驗證錯誤訊息
        console_output = capsys.readouterr().out
        assert "載入commit-assistant config 失敗" in console_output
