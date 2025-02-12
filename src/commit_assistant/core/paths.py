"""此模組用來統一管理專案中所有的路徑設定

集中管理所有專案中使用到的路徑，包括：
- 專案根目錄
- 套件目錄
- 資源檔案目錄
- 設定檔路徑
- 模板檔案路徑

優點：
1. 路徑邏輯集中管理，易於維護
2. 避免重複的路徑計算
3. 當專案結構改變時，只需要修改此處
"""

from pathlib import Path


class ProjectPaths:
    # 取得專案根目錄
    ROOT_DIR = Path(__file__).parent.parent.parent.parent

    # 套件相關路徑
    PACKAGE_DIR = Path(__file__).parent.parent
    RESOURCES_DIR = PACKAGE_DIR / "resources"

    # 配置相關路徑
    PYPROJECT_DIR = ROOT_DIR / "pyproject.toml"
    HOOKS_DIR = RESOURCES_DIR / "hooks"
    CONFIG_DIR = RESOURCES_DIR / "config"

    @classmethod
    def get_hook_template(cls, name: str) -> Path:
        """取得 hook 模板路徑"""
        return cls.HOOKS_DIR / name

    @classmethod
    def get_config_template(cls, name: str) -> Path:
        """取得設定檔模板路徑"""
        return cls.CONFIG_DIR / name
