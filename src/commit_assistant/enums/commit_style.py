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
