"""此模組負責產生專案的 pyproject.toml 設定檔

整合所有專案設定，包括：
1. 專案基本資料
2. 建置系統設定
3. 套件資訊

主要功能：
- 從各個設定來源收集資訊
- 組織並產生完整的 TOML 設定
- 確保設定格式的正確性
"""

from typing import Any, Dict

from .project_config import ProjectInfo


def generate_toml_config() -> Dict[str, Any]:
    """生成完整的 pyproject.toml 配置"""

    return {
        "tool": {
            "setuptools": {
                "package-data": ProjectInfo.PACKAGE_DATA,
                "packages": {
                    "find": {
                        "where": [ProjectInfo.PACKAGE_PATH],
                        "include": ProjectInfo.PACKAGE_INCLUDE,
                    }
                },
            },
        },
        "build-system": {
            "requires": ["setuptools>=45", "wheel"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": ProjectInfo.NAME,
            "version": ProjectInfo.VERSION,
            "description": ProjectInfo.DESCRIPTION,
            "requires-python": ProjectInfo.PYTHON_REQUIRES,
            "dependencies": ProjectInfo.get_dependencies(),
            "optional-dependencies": {
                "dev": ProjectInfo.get_dev_dependencies(),
            },
            "license": {"text": ProjectInfo.LICENSE},
            "scripts": {ProjectInfo.CLI_MAIN_COMMAND: ProjectInfo.ENTRY_POINTS},
        },
    }
