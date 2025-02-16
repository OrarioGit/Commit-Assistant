"""此模組用來統一管理專案的基本資訊，包括版本號、相依套件、專案名稱等。

此模組集中管理所有與專案相關的設定資訊，包括：
- 版本號管理
- 相依套件設定
- 專案基本資訊（名稱、描述等）
- 資源檔案設定
- 進入點(Entry Points)設定

這些資訊主要用於：
1. 產生 pyproject.toml 設定檔
2. 提供其他模組存取專案資訊
3. 版本控制與更新檢查
"""

from enum import Enum
from typing import List


class ProjectInfo:
    NAME: str = "commit-assistant"
    VERSION: str = "0.1.4"
    DESCRIPTION: str = "Commit Assistant - 一個幫助你更好寫 commit message 的 CLI 工具"
    PYTHON_REQUIRES: str = ">=3.9"
    LICENSE: str = "Apache-2.0"

    # 專案的相依套件
    class Dependencies(Enum):
        CLICK = "click>=8.0.0"
        PYTHON_DOTENV = "python-dotenv>=1.0.1"
        GOOGLE_GENERATIVEAI = "google-generativeai>=0.8.4"
        QUESTIONARY = "questionary>=2.1.0"
        RICH = "rich>=13.9.4"
        PYPERCLIP = "pyperclip>=1.9.0"
        TOMLI = "tomli>=2.2.1"
        TOMLW = "tomli-w>=1.2.0"

    # 專案開發的相依套件
    # 僅有開發時才需要的套件
    class DevDependencies(Enum):
        PRE_COMMIT = "pre-commit>=4.1.0"
        PYTEST = "pytest>=8.3.4"
        PYTEST_COV = "pytest-cov>=6.0.0"

    # 專案的package路徑
    PACKAGE_PATH = "src"
    PACKAGE_INCLUDE = ["commit_assistant*"]

    # 專案的主要指令
    # 這個指令會在安裝時被安裝到系統中，使用者也透過此命令來呼叫專案的功能
    CLI_MAIN_COMMAND = "commit-assistant"

    # 專案入口
    ENTRY_POINTS = "commit_assistant.cli:cli"

    # 設定專案的靜態檔案，此裡面包含的檔案，會在安裝時一併被安裝到專案中
    PACKAGE_DATA = {
        "commit_assistant": [
            "resources/**/*",
            "resources/hooks/*",
            "resources/config/*",
            "resources/config/.commit-assistant-config",
        ]
    }

    # hook template 名稱
    HOOK_TEMPLATE_NAME = "prepare-commit-msg"

    # 設定檔 template 名稱
    CONFIG_TEMPLATE_NAME = ".commit-assistant-config"

    # 會在使用者專案底下建立我們的專案管理目錄名稱
    REPO_ASSISTANT_DIR = ".commit-assistant"

    # 用來記錄比如使用者安裝的版本號、repo路徑等資訊
    INSTALLATIONS_FILE = "installations.toml"

    # unit test相關
    TEST_DIRS = ["commit-assistant"]
    TEST_COMMAND = (
        "--cov=commit_assistant --cov-branch --cov-report=term-missing --cov-report=html --cov-report=xml -v"
    )

    # 要忽略的檔案
    OMIT_FILES = [
        "tests/*",
        "*/__init__.py",
    ]

    # 最低的測試覆蓋率要求
    COVERAGE_THRESHOLD = 90
    EXCLUDE_LINES = [
        "pragma: no cover",
        "def __repr__",
        "if TYPE_CHECKING",
        "if __name__ == '__main__'",
    ]

    @classmethod
    def get_dependencies(cls) -> List[str]:
        """取得專案的相依套件清單"""
        return [dep.value for dep in cls.Dependencies]

    @classmethod
    def get_dev_dependencies(cls) -> List[str]:
        """取得專案的開發相依套件清單"""
        return [dep.value for dep in cls.DevDependencies]
