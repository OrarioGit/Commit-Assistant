from commit_assistant.core.project_config import ProjectInfo


def test_project_info_constants() -> None:
    """測試專案基本資訊常數"""
    assert isinstance(ProjectInfo.NAME, str)
    assert isinstance(ProjectInfo.VERSION, str)
    assert isinstance(ProjectInfo.DESCRIPTION, str)
    assert isinstance(ProjectInfo.PYTHON_REQUIRES, str)
    assert isinstance(ProjectInfo.LICENSE, str)

    # 驗證版本格式
    version_parts = ProjectInfo.VERSION.split(".")
    assert len(version_parts) == 3
    assert all(part.isdigit() for part in version_parts)

    # 驗證 Python 版本要求格式
    assert ProjectInfo.PYTHON_REQUIRES.startswith(">=")
    assert ProjectInfo.PYTHON_REQUIRES[2:].replace(".", "").isdigit()


def test_dependencies_enum() -> None:
    """測試相依套件列舉"""
    # 檢查所有相依套件的格式
    for dep in ProjectInfo.get_dependencies():
        # 檢查格式是否為 "package>=version"
        package, version = dep.split(">=")
        assert package.strip()  # 確保套件名稱不為空
        assert version.strip()  # 確保版本不為空
        assert all(part.isdigit() for part in version.split("."))


def test_dev_dependencies_enum() -> None:
    """測試開發相依套件列舉"""
    for dep in ProjectInfo.get_dev_dependencies():
        package, version = dep.split(">=")
        assert package.strip()
        assert version.strip()
        assert all(part.isdigit() for part in version.split("."))


def test_get_dependencies() -> None:
    """測試取得相依套件清單"""
    deps = ProjectInfo.get_dependencies()
    dependencies = ProjectInfo.Dependencies

    assert isinstance(deps, list)
    assert len(deps) == len(dependencies)
    assert all(isinstance(dep, str) for dep in deps)
    assert all(dep.value in deps for dep in dependencies)


def test_get_dev_dependencies() -> None:
    """測試取得開發相依套件清單"""
    dev_deps = ProjectInfo.get_dev_dependencies()
    dev_dependencies = ProjectInfo.DevDependencies

    assert isinstance(dev_deps, list)
    assert len(dev_deps) == len(dev_dependencies)
    assert all(isinstance(dep, str) for dep in dev_deps)
    assert all(dep.value in dev_deps for dep in dev_dependencies)


def test_package_data() -> None:
    """測試套件資料設定"""
    assert "commit_assistant" in ProjectInfo.PACKAGE_DATA
    package_files = ProjectInfo.PACKAGE_DATA["commit_assistant"]
    assert isinstance(package_files, list)
    assert "resources/**/*" in package_files
    assert "resources/hooks/*" in package_files
    assert "resources/config/*" in package_files


def test_test_settings() -> None:
    """測試測試相關設定"""
    assert isinstance(ProjectInfo.TEST_DIRS, list)
    assert isinstance(ProjectInfo.TEST_COMMAND, str)
    assert isinstance(ProjectInfo.COVERAGE_THRESHOLD, int)
    assert 0 <= ProjectInfo.COVERAGE_THRESHOLD <= 100

    assert isinstance(ProjectInfo.OMIT_FILES, list)
    assert isinstance(ProjectInfo.EXCLUDE_LINES, list)
    assert "pragma: no cover" in ProjectInfo.EXCLUDE_LINES


def test_file_names() -> None:
    """測試檔案名稱設定"""
    assert ProjectInfo.HOOK_TEMPLATE_NAME == "prepare-commit-msg"
    assert ProjectInfo.CONFIG_TEMPLATE_NAME.startswith(".")
    assert ProjectInfo.REPO_ASSISTANT_DIR.startswith(".")
    assert ProjectInfo.INSTALLATIONS_FILE.endswith(".toml")
