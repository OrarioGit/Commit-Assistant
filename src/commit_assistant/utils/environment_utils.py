"""執行環境偵測

commit-assistant 的互動流程（選單、編輯器）只適合人類在終端機中操作。
當 commit 是由 AI agent（如 Claude Code）或沒有終端機的環境（IDE GUI、CI）發起時，
應該完全不介入，讓呼叫端自己決定 commit message。
"""

import os
import sys

# AI agent 執行指令時會帶上的環境變數
# 需與 resources/hooks/prepare-commit-msg 中的檢查保持一致
AGENT_ENV_VARS = [
    "CLAUDECODE",  # Claude Code
    "AI_AGENT",  # 跨工具的 agent 識別慣例
    "GEMINI_CLI",  # Gemini CLI
    "CODEX_SANDBOX",  # OpenAI Codex CLI
    "CURSOR_AGENT",  # Cursor agent
]


def is_agent_environment() -> bool:
    """是否由 AI agent 發起

    Returns:
        bool: 偵測到任一 agent 環境變數時回傳 True
    """
    return any(os.getenv(var) for var in AGENT_ENV_VARS)


def is_interactive_environment() -> bool:
    """是否適合進行互動式操作

    Returns:
        bool: 由人類在終端機中操作時回傳 True
    """
    if is_agent_environment():
        return False

    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False
