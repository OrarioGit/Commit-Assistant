from pathlib import Path
from typing import get_type_hints

import pytest

from commit_assistant.core.paths import ProjectPaths


def test_project_paths_constants() -> None:
    """測試路徑常數是否正確設定"""
    # 檢查基本路徑
    assert isinstance(ProjectPaths.ROOT_DIR, Path)
    assert isinstance(ProjectPaths.PACKAGE_DIR, Path)
    assert isinstance(ProjectPaths.RESOURCES_DIR, Path)

    # 檢查路徑關係
    assert ProjectPaths.PACKAGE_DIR == Path(__file__).parent.parent / "src" / "commit_assistant"
    assert ProjectPaths.RESOURCES_DIR == ProjectPaths.PACKAGE_DIR / "resources"
    assert ProjectPaths.HOOKS_DIR == ProjectPaths.RESOURCES_DIR / "hooks"
    assert ProjectPaths.CONFIG_DIR == ProjectPaths.RESOURCES_DIR / "config"


def test_prevent_inheritance() -> None:
    """測試防止繼承"""
    # 測試類型標記
    with pytest.raises(TypeError, match="不能被繼承"):
        ProjectPaths.__class_getitem__(None)

    # 測試直接繼承
    with pytest.raises(TypeError, match="不能被繼承"):

        class SubClass(ProjectPaths):
            pass


def test_prevent_attribute_modification() -> None:
    """測試防止修改屬性"""
    paths = ProjectPaths()

    with pytest.raises(AttributeError, match="不能修改.*的屬性"):
        paths.ROOT_DIR = Path("/another/path")  # type: ignore

    with pytest.raises(AttributeError, match="不能修改.*的屬性"):
        paths.NEW_ATTR = "value"


def test_get_hook_template() -> None:
    """測試獲取 hook 模板路徑"""
    hook_name = "prepare-commit-msg"
    template_path = ProjectPaths.get_hook_template(hook_name)

    assert isinstance(template_path, Path)
    assert template_path == ProjectPaths.HOOKS_DIR / hook_name


def test_get_config_template() -> None:
    """測試獲取設定檔模板路徑"""
    config_name = "config.toml"
    template_path = ProjectPaths.get_config_template(config_name)

    assert isinstance(template_path, Path)
    assert template_path == ProjectPaths.CONFIG_DIR / config_name


def test_class_attributes_are_paths() -> None:
    """測試所有類別屬性都是 Path 物件"""
    # 取得所有大寫的類別屬性（慣例上的常數）
    path_attrs = [attr for attr in dir(ProjectPaths) if attr.isupper()]

    for attr in path_attrs:
        value = getattr(ProjectPaths, attr)
        assert isinstance(value, Path), f"{attr} 應該是 Path 物件"


def test_path_attributes_are_final() -> None:
    """測試路徑屬性是否為 Final"""

    hints = get_type_hints(ProjectPaths)
    for attr, hint in hints.items():
        if attr.isupper():  # 只檢查大寫的屬性（常數）
            assert str(hint).startswith("typing.Final"), f"{attr} 應該被標記為 Final"
