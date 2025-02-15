"""此模組提供設定檔的建置與更新功能

主要功能：
1. 讀取專案基本資料與設定
2. 產生或更新 pyproject.toml 檔案
3. 提供命令列介面以便手動更新設定

使用方式：
    python -m commit_assistant.script.build_pyproject

注意：
- 使用前請先執行 pip install -e . 將專案安裝到本地環境(建議使用虛擬環境)
- 執行此模組會覆寫現有的 pyproject.toml
- 建議在修改版本號或設定後執行
"""

import tomli_w

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.pyproject_config import generate_toml_config


def update_pyproject_toml() -> None:
    """更新 pyproject.toml 檔案"""
    config = generate_toml_config()
    project_root = ProjectPaths.ROOT_DIR
    toml_path = project_root / "pyproject.toml"

    with open(toml_path, "wb") as f:
        tomli_w.dump(config, f)


if __name__ == "__main__":  # pragma: no cover
    update_pyproject_toml()
