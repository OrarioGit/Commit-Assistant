import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from commit_assistant.utils.hook_manager import HookManager, HookVersion


@pytest.fixture
def hook_manager(tmp_path: Path) -> HookManager:
    """建立測試用的 HookManager"""
    return HookManager(tmp_path)


@pytest.fixture
def git_hooks_dir(tmp_path: Path) -> Path:
    """建立測試用的 .git/hooks 目錄"""
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return hooks_dir


@pytest.fixture
def husky_dir(tmp_path: Path) -> Path:
    """建立測試用的 .husky 目錄"""
    husky_dir = tmp_path / ".husky"
    husky_dir.mkdir()
    return husky_dir


def test_backup_existing_hook(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試備份現有的 hook"""
    # 建立測試用的 hook 檔案
    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text("original content")

    with patch("commit_assistant.utils.hook_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 2, 14, 12, 0, 0)

        backup_path = hook_manager._backup_existing_hook()

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name == "prepare-commit-msg.backup_20240214_120000"
        assert backup_path.read_text() == "original content"


def test_backup_existing_hook_no_hook(hook_manager: HookManager) -> None:
    """測試備份現有的 hook，但不存在 hook 檔案"""
    backup_path = hook_manager._backup_existing_hook()

    assert backup_path is None


def test_detect_husky_with_dir(hook_manager: HookManager, tmp_path: Path) -> None:
    """測試偵測 husky 目錄"""
    husky_dir = tmp_path / ".husky"
    husky_dir.mkdir()

    assert hook_manager._detect_husky() is True


def test_detect_husky_with_package_json(hook_manager: HookManager, tmp_path: Path) -> None:
    """測試偵測 package.json 中的 husky"""
    package_json = tmp_path / "package.json"
    package_json.write_text('{"devDependencies": {"husky": "^8.0.0"}}')

    assert hook_manager._detect_husky() is True


def test_detect_husky_with_package_json_error(hook_manager: HookManager, tmp_path: Path) -> None:
    """測試偵測 package.json 中的 husky，但發生錯誤"""
    package_json = tmp_path / "package.json"
    package_json.write_text('{"devDependencies": {"husky": "^8.0.0"}')

    # open 的時候發生錯誤
    with patch("commit_assistant.utils.hook_manager.open", side_effect=Exception("Test Error")):
        assert hook_manager._detect_husky() is False


def test_detect_hook_version(hook_manager: HookManager) -> None:
    """測試偵測 hook 版本"""
    new_content = (
        f"{HookManager.COMMIT_ASSISTANT_MARKER_START}\ncontent\n{HookManager.COMMIT_ASSISTANT_MARKER_END}"
    )
    old_content = f"{HookManager.OLD_MARKER}\ncontent"
    no_marker_content = "some content"

    assert hook_manager._detect_hook_version(new_content) == HookVersion.NEW
    assert hook_manager._detect_hook_version(old_content) == HookVersion.OLD
    assert hook_manager._detect_hook_version(no_marker_content) == HookVersion.NOT_INSTALLED


def test_install_hook_git(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試安裝 git hook"""
    hook_content = "test hook content"
    hook_manager.install_hook(hook_content)

    hook_path = git_hooks_dir / "prepare-commit-msg"
    assert hook_path.exists()
    # 根據作業系統檢查權限
    if sys.platform != "win32":
        # Unix/Linux 系統檢查 755 權限
        assert hook_path.stat().st_mode & 0o777 == 0o755
    else:
        # Windows 系統確保檔案可以執行
        assert os.access(str(hook_path), os.X_OK)

    # 確保新版的Marker存在
    content = hook_path.read_text()
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in content
    assert hook_content in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in content


def test_install_hook_git_with_backup(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試安裝 git hook，且備份"""

    with patch("commit_assistant.utils.hook_manager.HookManager._backup_existing_hook") as mock_backup:
        mock_backup.return_value = "some_backup_path"  # 模擬備份完畢

        hook_content = "test hook content"
        hook_manager.install_hook(hook_content)

    hook_path = git_hooks_dir / "prepare-commit-msg"
    assert hook_path.exists()
    # 根據作業系統檢查權限
    if sys.platform != "win32":
        # Unix/Linux 系統檢查 755 權限
        assert hook_path.stat().st_mode & 0o777 == 0o755
    else:
        # Windows 系統確保檔案可以執行
        assert os.access(str(hook_path), os.X_OK)

    # 確保新版的Marker存在
    content = hook_path.read_text()
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in content
    assert hook_content in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in content


def test_install_hook_husky(hook_manager: HookManager, tmp_path: Path) -> None:
    """測試安裝 husky hook"""
    # 建立 husky 目錄
    husky_dir = tmp_path / ".husky"
    husky_dir.mkdir()

    hook_content = "test husky hook content"
    hook_manager.install_hook(hook_content)

    hook_path = husky_dir / "prepare-commit-msg"
    assert hook_path.exists()
    # 根據作業系統檢查權限
    if sys.platform != "win32":
        # Unix/Linux 系統檢查 755 權限
        assert hook_path.stat().st_mode & 0o777 == 0o755
    else:
        # Windows 系統確保檔案可以執行
        assert os.access(str(hook_path), os.X_OK)

    content = hook_path.read_text()
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in content
    assert hook_content in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in content


def test_install_hook_husky_and_husky_hook_already_exists(hook_manager: HookManager, tmp_path: Path) -> None:
    """測試安裝 husky hook，但 husky hook 已經存在，且不包含新版的 marker"""
    # 建立 husky 目錄
    husky_dir = tmp_path / ".husky"
    husky_dir.mkdir()

    # 建立 prepare-commit-msg hook
    hook_path = husky_dir / "prepare-commit-msg"
    hook_path.write_text(
        "original content",
        encoding="utf-8",
    )

    hook_content = "test husky hook content"
    hook_manager.install_hook(hook_content)

    content = hook_path.read_text(encoding="utf-8")

    # 由於檔案存在，不應該被覆蓋
    assert content != hook_content
    assert "original content" in content

    # 檢查新版的 hook 是否有被加入
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in content
    assert "test husky hook content" in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in content


def test_install_hook_husky_and_husky_hook_already_exists_new_version(
    hook_manager: HookManager, tmp_path: Path
) -> None:
    """測試安裝 husky hook，但 husky hook 已經存在，且已經是新版的 marker"""
    # 建立 husky 目錄
    husky_dir = tmp_path / ".husky"
    husky_dir.mkdir()

    # 建立 prepare-commit-msg hook
    hook_path = husky_dir / "prepare-commit-msg"
    hook_path.write_text(
        f"original content\n{HookManager.COMMIT_ASSISTANT_MARKER_START}\nold hook content\n{HookManager.COMMIT_ASSISTANT_MARKER_END}",
        encoding="utf-8",
    )

    hook_content = "test husky hook content"
    hook_manager.install_hook(hook_content)

    content = hook_path.read_text(encoding="utf-8")

    # 由於檔案存在，不應該被覆蓋
    assert content != hook_content
    assert "original content" in content
    assert "test husky hook content" not in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in content
    assert "old hook content" in content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in content


def test_inject_hooks_without_our_hook(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試注入 hooks，且使用者未安裝我們的 hook"""
    # 新增一個不包含新版的 marker，模擬使用者自行新增的內容
    original_content = "#!/bin/sh\noriginal content"
    new_content = "new content"

    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text(original_content, encoding="utf-8")

    injected = hook_manager._inject_hooks(new_content)

    assert "#!/bin/sh" in injected
    assert "original content" in injected

    # 確認我們的內容有成功注入
    assert new_content in injected
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in injected
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in injected


def test_inject_hooks_with_our_hook(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試注入 hooks，但使用者已經安裝過我們的 hook"""
    # 包含新版的 marker，模擬已經安裝過的情況
    original_content = "#!/bin/sh\noriginal content\n"
    original_content += f"{HookManager.COMMIT_ASSISTANT_MARKER_START}\nold hook content\n{HookManager.COMMIT_ASSISTANT_MARKER_END}"
    new_content = "new content"

    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text(original_content, encoding="utf-8")

    injected = hook_manager._inject_hooks(new_content)

    assert HookManager.COMMIT_ASSISTANT_MARKER_START in injected
    assert "original content" in injected  # 保留使用者的內容
    assert "old hook content" in injected
    assert new_content not in injected  # 使用者已經注入過，不應該再次注入
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in injected


def test_update_git_hook(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試更新 git hook"""
    # 建立舊版本的 hook
    old_content = f"{HookManager.OLD_MARKER}\nold content"
    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    new_content = "new content"
    hook_manager.update_hook(new_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_git_hook_without_exist_hook(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試更新 hook，但原本的 hook 不存在"""

    new_content = "new content"
    hook_manager.update_hook(new_content)

    # 檢查是否有新建立 hook於 git路徑中
    hook_path = git_hooks_dir / "prepare-commit-msg"
    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_git_hook_without_new_version_mark(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試更新 hook，但原本的hook 卻沒有包含新版或舊版的 marker"""
    # 建立舊版本的 hook
    old_content = f"{HookManager.COMMIT_ASSISTANT_MARKER_START}\nold hook content\n{HookManager.COMMIT_ASSISTANT_MARKER_END}"
    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    with patch(
        "commit_assistant.utils.hook_manager.HookManager._replace_commit_assistant_section"
    ) as mock_replace:
        # 這裡讓兩者一樣，模擬當前版本的 hook 已經是最新版本的情況
        mock_replace.return_value = old_content
        hook_manager.update_hook(old_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert old_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_git_hook_but_already_newest(hook_manager: HookManager, git_hooks_dir: Path) -> None:
    """測試更新 hook，但原本的hook 已經是最新版本"""
    # 建立舊版本的 hook
    old_content = "old content"
    hook_path = git_hooks_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    new_content = "new content"
    hook_manager.update_hook(new_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_extract_old_hook_content_old_marker_not_found(hook_manager: HookManager) -> None:
    """測試從舊版的 hook 中取出內容，但找不到舊版的 marker"""
    # 沒有舊版的 marker
    old_content = "old content"
    extracted = hook_manager._extract_old_hook_content(old_content)

    assert extracted == ""

    # 沒有換行符號
    old_content = f"{HookManager.OLD_MARKER}old content"
    extracted = hook_manager._extract_old_hook_content(old_content)

    assert extracted == ""

    # 沒有任何內容
    old_content = f"{HookManager.OLD_MARKER}"
    extracted = hook_manager._extract_old_hook_content(old_content)

    assert extracted == ""


def test_migrate_to_new_format_old_marker_not_found(hook_manager: HookManager) -> None:
    """測試從舊版本的 hook 中提取 commit-assistant 的內容，但找不到舊版的 marker"""
    # 沒有舊版的 marker
    old_content = "old content"
    extracted = hook_manager._migrate_to_new_format(old_content)

    # 沒有找到舊版的 marker，應該要直接返回原本的內容
    assert extracted == old_content


def test_update_husky_hook(hook_manager: HookManager, husky_dir: Path) -> None:
    """測試更新 husky hook"""
    # 建立舊版本的 hook
    old_content = (
        f"{HookManager.COMMIT_ASSISTANT_MARKER_START}\nold content\n{HookManager.COMMIT_ASSISTANT_MARKER_END}"
    )
    hook_path = husky_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    new_content = "new content"
    hook_manager.update_hook(new_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_husky_hook_without_exist_hook(hook_manager: HookManager, husky_dir: Path) -> None:
    """測試更新 husky hook，但原本的 hook 不存在"""

    new_content = "new content"
    hook_manager.update_hook(new_content)

    # 檢查是否有新建立 hook於 husky路徑中
    hook_path = husky_dir / "prepare-commit-msg"
    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_husky_hook_with_old_version_hook(hook_manager: HookManager, husky_dir: Path) -> None:
    """測試更新 husky hook，但原本的 hook 是舊版的 marker"""
    # 建立舊版本的 hook
    old_content = f"{HookManager.OLD_MARKER}\nold content"
    hook_path = husky_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    new_content = "new content"
    hook_manager.update_hook(new_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert new_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除


def test_update_husky_hook_but_already_newest(hook_manager: HookManager, husky_dir: Path) -> None:
    """測試更新 hook，但原本的hook 已經是最新版本"""
    # 建立舊版本的 hook
    old_content = (
        f"{HookManager.COMMIT_ASSISTANT_MARKER_START}\nold content\n{HookManager.COMMIT_ASSISTANT_MARKER_END}"
    )
    hook_path = husky_dir / "prepare-commit-msg"
    hook_path.write_text(old_content, encoding="utf-8")

    with patch(
        "commit_assistant.utils.hook_manager.HookManager._replace_commit_assistant_section"
    ) as mock_replace:
        mock_replace.return_value = old_content  # 這裡讓兩者一樣，模擬當前版本的 hook 已經是最新版本的情況
        hook_manager.update_hook(old_content)

    updated_content = hook_path.read_text(encoding="utf-8")
    assert HookManager.COMMIT_ASSISTANT_MARKER_START in updated_content
    assert old_content in updated_content
    assert HookManager.COMMIT_ASSISTANT_MARKER_END in updated_content
    assert HookManager.OLD_MARKER not in updated_content  # 確認舊的 marker 已經被移除
