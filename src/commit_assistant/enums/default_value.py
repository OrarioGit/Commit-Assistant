from enum import Enum


class DefaultValue(Enum):
    # Gemini 2.5 Flash 已棄用，官方指定的替代模型為 gemini-3.5-flash-lite
    DEFAULT_MODEL = "gemini-3.5-flash-lite"

    # 實測 sonnet 搭配低 effort 的回應速度比 haiku 快，用量也遠低於 opus
    DEFAULT_CLAUDE_CLI_MODEL = "sonnet"

    # 實測 low 與預設 effort 產出的 commit message 與重要提醒幾乎相同，用量約少一半
    DEFAULT_CLAUDE_CLI_EFFORT = "low"
