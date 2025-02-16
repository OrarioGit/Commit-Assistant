from pathlib import Path
from typing import Dict, Generator

import pytest

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.update_utils import UpdateManager


@pytest.fixture
def update_manager(tmp_path: Path) -> UpdateManager:
    """建立測試用的 UpdateManager"""
    return UpdateManager(tmp_path)


@pytest.fixture
def mock_template_paths(tmp_path: Path, update_manager: UpdateManager) -> Generator[Dict, None, None]:
    """建立模擬的模板檔案"""
    # 建立測試用的模板目錄結構
    git_hook_dir = tmp_path / ".git" / "hooks"
    hooks_dir = tmp_path / "hooks"
    config_dir = tmp_path / "config"
    resources_dir = tmp_path / "resources"

    git_hook_dir.mkdir(parents=True)
    hooks_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    # 建立測試用的模板檔案
    (hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME).write_text("test hook content", encoding="utf-8")
    (config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME).write_text(
        """# test config
            COMMIT_STYLE=custom
            ENABLE_COMMIT_ASSISTANT=true""",
        encoding="utf-8",
    )

    update_manager.hook_path = git_hook_dir / ProjectInfo.HOOK_TEMPLATE_NAME
    update_manager.hook_template_path = hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME
    update_manager.config_template_path = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME

    yield {"HOOKS_DIR": hooks_dir, "CONFIG_DIR": config_dir, "RESOURCES_DIR": resources_dir}


def test_read_template_config(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試讀取模板設定"""
    # 設定模板路徑
    # update_manager.config_template_path = mock_template_paths["CONFIG_DIR"] / ProjectInfo.CONFIG_TEMPLATE_NAME

    config = update_manager._read_template_config()
    assert config == {"COMMIT_STYLE": "custom", "ENABLE_COMMIT_ASSISTANT": "true"}


def test_parse_config_content(update_manager: UpdateManager) -> None:
    """測試解析設定內容"""
    content = """
        # comment line
        KEY1=value1
        KEY2=value2

        # another comment
        KEY3=value3 with spaces
    """

    config = update_manager._parse_config_content(content)
    assert config == {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3 with spaces"}


def test_merge_configs(update_manager: UpdateManager) -> None:
    """測試合併設定"""
    current_config = {"COMMIT_STYLE": "custom", "OLD_KEY": "old_value"}
    new_config = {"COMMIT_STYLE": "conventional", "ENABLE_COMMIT_ASSISTANT": "true"}

    merged = update_manager._merge_configs(current_config, new_config)

    assert merged == {
        "COMMIT_STYLE": "custom",  # 保留使用者的設定
        "ENABLE_COMMIT_ASSISTANT": "true",  # 新增的設定
    }


def test_update_config(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試更新設定檔"""
    # 建立現有的設定檔
    config_dir = update_manager.repo_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir(parents=True)
    config_path = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME
    config_path.write_text(
        """
        COMMIT_STYLE=custom
        OLD_SETTING=value
    """,
        encoding="utf-8",
    )

    update_manager._update_config()

    # 檢查更新後的設定檔
    updated_content = config_path.read_text(encoding="utf-8")
    assert "COMMIT_STYLE=custom" in updated_content  # 保留使用者設定
    assert "ENABLE_COMMIT_ASSISTANT=true" in updated_content  # 新增的設定
    assert "OLD_SETTING" not in updated_content  # 確認舊的設定已被移除


def test_update_with_old_config_migration(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試舊版設定檔遷移"""
    # 建立舊版設定檔
    old_config = update_manager.repo_path / ProjectInfo.CONFIG_TEMPLATE_NAME
    old_config.write_text("COMMIT_STYLE=custom")

    update_manager.update()

    # 確認舊檔案被移動到新位置
    assert not old_config.exists()
    new_config = update_manager.repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME
    assert new_config.exists()
    assert "COMMIT_STYLE=custom" in new_config.read_text()


def test_update_config_without_config_path(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試更新設定檔"""
    # 如果update_manager.config_path存在，則先刪除
    if update_manager.config_path.exists():
        update_manager.config_path.unlink()

    update_manager._update_config()

    # 檢查更新後的設定檔
    updated_content = update_manager.config_path.read_text(encoding="utf-8")
    assert "COMMIT_STYLE=custom" in updated_content  # 保留使用者設定
    assert "ENABLE_COMMIT_ASSISTANT=true" in updated_content  # 新增的設定


def test_update(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試更新功能且不需要遷移舊版設定檔"""
    update_manager.update()
    new_config = update_manager.repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME
    assert new_config.exists()
    assert "COMMIT_STYLE=custom" in new_config.read_text()
