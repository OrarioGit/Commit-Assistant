"""專案的Script模組，提供了專案一些基本的腳本功能

此套件包含：
- build_pyproject: 用來建置或更新 pyproject.toml 檔案

這些模組共同提供了專案的擴充腳本，方便開發者進行一些額外的操作
"""

from .build_pyproject import update_pyproject_toml

__all__ = ["update_pyproject_toml"]
