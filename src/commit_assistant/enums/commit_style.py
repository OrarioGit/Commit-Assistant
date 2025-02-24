from enum import Enum


class CommitStyle(Enum):
    """Commit Style 列舉類別

    用來定義 commit message 的風格，目前支援以下風格：
    - ANGULAR: Angular 風格
    - CONVENTIONAL: Conventional Commits 風格
    - EMOJI: Emoji 風格
    - CUSTOM: 自訂風格
    """

    ANGULAR = "angular"
    CONVENTIONAL = "conventional"
    EMOJI = "emoji"
    CUSTOM = "custom"


class StyleScope(Enum):
    """Style Scope 列舉類別

    用來定義 style 的層級，目前支援以下範圍：
    - SYSTEM: 系統內建的 style（套件提供的預設 style）
    - GLOBAL: 提供使用者全域使用層級的 style (可供所有專案使用)
    - PROJECT: 專案層級的 style (只能在該專案內使用)
    """

    SYSTEM = "系統內建"
    GLOBAL = "全域自訂"
    PROJECT = "專案自訂"
