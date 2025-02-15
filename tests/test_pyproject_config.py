from typing import Any, Dict

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.core.pyproject_config import generate_toml_config


def test_generate_toml_config() -> None:
    """測試生成 pyproject.toml 配置"""
    config = generate_toml_config()

    # 檢查主要區段是否存在
    assert "tool" in config
    assert "build-system" in config
    assert "project" in config

    # 檢查 tool 區段
    tool = config["tool"]
    assert "setuptools" in tool
    assert "pytest" in tool
    assert "coverage" in tool

    # 檢查 setuptools 設定
    setuptools = tool["setuptools"]
    assert setuptools["package-data"] == ProjectInfo.PACKAGE_DATA
    assert setuptools["packages"]["find"]["where"] == [ProjectInfo.PACKAGE_PATH]
    assert setuptools["packages"]["find"]["include"] == ProjectInfo.PACKAGE_INCLUDE

    # 檢查 pytest 設定
    pytest = tool["pytest"]
    assert pytest["ini_options"]["addopts"] == ProjectInfo.TEST_COMMAND

    # 檢查 coverage 設定
    coverage = tool["coverage"]
    assert coverage["run"]["source"] == ProjectInfo.TEST_DIRS
    assert coverage["run"]["omit"] == ProjectInfo.OMIT_FILES
    assert coverage["report"]["fail_under"] == ProjectInfo.COVERAGE_THRESHOLD
    assert coverage["report"]["exclude_lines"] == ProjectInfo.EXCLUDE_LINES

    # 檢查 build-system 設定
    build_system = config["build-system"]
    assert "setuptools>=45" in build_system["requires"]
    assert "wheel" in build_system["requires"]
    assert build_system["build-backend"] == "setuptools.build_meta"

    # 檢查 project 設定
    project = config["project"]
    assert project["name"] == ProjectInfo.NAME
    assert project["version"] == ProjectInfo.VERSION
    assert project["description"] == ProjectInfo.DESCRIPTION
    assert project["requires-python"] == ProjectInfo.PYTHON_REQUIRES
    assert project["dependencies"] == ProjectInfo.get_dependencies()
    assert project["optional-dependencies"]["dev"] == ProjectInfo.get_dev_dependencies()
    assert project["license"]["text"] == ProjectInfo.LICENSE
    assert project["scripts"][ProjectInfo.CLI_MAIN_COMMAND] == ProjectInfo.ENTRY_POINTS


def test_config_structure_validity() -> None:
    """測試配置結構的有效性"""
    config = generate_toml_config()

    # 確保所有值的型別正確
    def validate_dict_types(d: Dict[str, Any], path: str = "") -> None:
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key

            # 檢查鍵是否為字串
            assert isinstance(key, str), f"Key at {current_path} should be string"

            # 遞迴檢查字典
            if isinstance(value, dict):
                validate_dict_types(value, current_path)
            # 檢查列表內容
            elif isinstance(value, list):
                for item in value:
                    assert isinstance(item, (str, dict)), (
                        f"List items at {current_path} should be string or dict"
                    )
            # 檢查基本型別
            else:
                assert isinstance(value, (str, int, bool, list)), (
                    f"Value at {current_path} has invalid type: {type(value)}"
                )

    validate_dict_types(config)


def test_required_fields_present() -> None:
    """測試必要欄位是否存在且非空"""
    config = generate_toml_config()

    required_fields = {
        "project.name": lambda c: c["project"]["name"],
        "project.version": lambda c: c["project"]["version"],
        "project.description": lambda c: c["project"]["description"],
        "project.requires-python": lambda c: c["project"]["requires-python"],
        "project.dependencies": lambda c: c["project"]["dependencies"],
    }

    for field_name, getter in required_fields.items():
        value = getter(config)
        assert value, f"{field_name} should not be empty"
