"""專案的核心模組，提供基礎設定與功能

此套件包含：
- project_config: 專案基本資料管理
- paths: 專案路徑管理
- pyproject_config: 設定檔建置工具
- base_generator: Gemini AI 生成器的基礎類別模組

這些模組共同提供了專案的基礎設施，確保：
1. 版本與相依套件的一致性
2. 專案結構的可維護性
3. 共用類別的重用性
"""

from .base_generator import BaseGeminiAIGenerator
from .paths import ProjectPaths
from .project_config import ProjectInfo
from .pyproject_config import generate_toml_config

__all__ = ["BaseGeminiAIGenerator", "ProjectPaths", "ProjectInfo", "generate_toml_config"]
