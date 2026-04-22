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
    git_hook_dir = tmp_path / ".git" / "hooks"
    hooks_dir = tmp_path / "hooks"
    config_dir = tmp_path / "config"
    resources_dir = tmp_path / "resources"

    git_hook_dir.mkdir(parents=True)
    hooks_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    (hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME).write_text("test hook content", encoding="utf-8")
    (config_dir / ProjectInfo.CONFIG_EXAMPLE_NAME).write_text(
        "# test example config\nCOMMIT_STYLE=conventional\nENABLE_COMMIT_ASSISTANT=true",
        encoding="utf-8",
    )
    (resources_dir / ProjectInfo.INSTALLATIONS_FILE).write_text("", encoding="utf-8")

    update_manager.hook_path = git_hook_dir / ProjectInfo.HOOK_TEMPLATE_NAME
    update_manager.hook_template_path = hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME
    update_manager.example_template_path = config_dir / ProjectInfo.CONFIG_EXAMPLE_NAME
    update_manager.example_config_path = (
        tmp_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_EXAMPLE_NAME
    )
    update_manager.installations_path = resources_dir / ProjectInfo.INSTALLATIONS_FILE

    yield {"HOOKS_DIR": hooks_dir, "CONFIG_DIR": config_dir, "RESOURCES_DIR": resources_dir}


def test_update_example_config(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試更新 example 設定檔"""
    update_manager._update_example_config()

    assert update_manager.example_config_path.exists()
    content = update_manager.example_config_path.read_text(encoding="utf-8")
    assert "COMMIT_STYLE=conventional" in content
    assert "ENABLE_COMMIT_ASSISTANT=true" in content


def test_update_example_config_creates_dir(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試 example 設定檔的父目錄不存在時自動建立"""
    assert not update_manager.example_config_path.parent.exists()

    update_manager._update_example_config()

    assert update_manager.example_config_path.exists()


def test_update_example_config_overwrites_existing(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """測試 example 設定檔已存在時會被最新模板覆蓋"""
    update_manager.example_config_path.parent.mkdir(parents=True, exist_ok=True)
    update_manager.example_config_path.write_text("# old content", encoding="utf-8")

    update_manager._update_example_config()

    content = update_manager.example_config_path.read_text(encoding="utf-8")
    assert "COMMIT_STYLE=conventional" in content


def test_migrate_pre_example_config_no_op_if_config_not_exists(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """若個人設定檔不存在，則不執行遷移"""
    assert not update_manager.config_path.exists()

    update_manager._migrate_pre_example_config()

    assert not update_manager.example_config_path.exists()


def test_migrate_pre_example_config_no_op_if_example_exists(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """若 example 檔已存在，則跳過遷移（不覆蓋）"""
    update_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    update_manager.config_path.write_text("COMMIT_STYLE=custom", encoding="utf-8")
    update_manager.example_config_path.parent.mkdir(parents=True, exist_ok=True)
    update_manager.example_config_path.write_text("# already exists", encoding="utf-8")

    update_manager._migrate_pre_example_config()

    assert "already exists" in update_manager.example_config_path.read_text(encoding="utf-8")


def test_migrate_pre_example_config_creates_example_and_gitignore(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """測試從舊版遷移：建立 example 檔並將個人設定加入 .gitignore"""
    update_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    update_manager.config_path.write_text("COMMIT_STYLE=custom", encoding="utf-8")

    update_manager._migrate_pre_example_config()

    assert update_manager.example_config_path.exists()
    gitignore = update_manager.repo_path / ".gitignore"
    assert gitignore.exists()
    assert ProjectInfo.CONFIG_TEMPLATE_NAME in gitignore.read_text(encoding="utf-8")


def test_migrate_pre_example_config_preserves_personal_config(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """遷移時不修改使用者既有的個人設定檔"""
    update_manager.config_path.parent.mkdir(parents=True, exist_ok=True)
    update_manager.config_path.write_text("COMMIT_STYLE=custom", encoding="utf-8")

    update_manager._migrate_pre_example_config()

    assert update_manager.config_path.read_text(encoding="utf-8") == "COMMIT_STYLE=custom"


def test_update_with_old_root_config_migration(
    update_manager: UpdateManager, mock_template_paths: Dict
) -> None:
    """測試舊版設定檔（放在根目錄）自動遷移至新位置"""
    old_config = update_manager.repo_path / ProjectInfo.CONFIG_TEMPLATE_NAME
    old_config.write_text("COMMIT_STYLE=custom")

    update_manager.update()

    assert not old_config.exists()
    new_config = update_manager.repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME
    assert new_config.exists()
    assert "COMMIT_STYLE=custom" in new_config.read_text()


def test_update(update_manager: UpdateManager, mock_template_paths: Dict) -> None:
    """測試正常更新流程：更新 example config 與 hook"""
    update_manager.update()

    assert update_manager.example_config_path.exists()
    content = update_manager.example_config_path.read_text(encoding="utf-8")
    assert "COMMIT_STYLE=conventional" in content
