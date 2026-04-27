"""AI 生成器的基礎類別模組

支援 Gemini API 與 Claude CLI 兩種 provider。
透過 USE_CLAUDE_CLI=true 啟用 Claude CLI 模式（不需要 API key，使用已經登入的 Claude Code）。
"""

import os
import subprocess
from typing import Optional

from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.enums.default_value import DefaultValue
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.style_utils import CommitStyleManager


class BaseGeminiAIGenerator:
    """建立一個 AI Generator 的基類，支援 Gemini API 和 Claude CLI"""

    def __init__(self) -> None:
        self._use_claude_cli = os.getenv(ConfigKey.USE_CLAUDE_CLI.value, "false").lower() == "true"

        if not self._use_claude_cli:
            from google import genai

            api_key = os.getenv("GEMINI_API_KEY")
            if api_key is None:
                console.print("[yellow] 檢測到尚未設定 Gemini api key [/yellow]")
                raise ValueError("請先執行 commit-assistant config setup 設定 API 金鑰")

            self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(str(ConfigKey.USE_MODEL.value), DefaultValue.DEFAULT_MODEL.value)
        self.style_manager = CommitStyleManager()

    def _generate_content(self, prompt: str) -> Optional[str]:
        try:
            if self._use_claude_cli:
                # 如果使用 claude code，直接呼叫 claude -p 來生成指定的內容
                # 使用 shell=True + stdin 來避免傳入的 prompt 過長的問題
                result = subprocess.run(
                    "claude -p",
                    input=prompt,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if result.returncode != 0:
                    console.print(f"[red]{result.stderr}[/red]")
                    return None
                return result.stdout.strip()
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                return response.text
        except Exception as e:
            console.print("[red] 生成內容時發生錯誤：[/red]")
            console.print(f"[red]{e}[/red]")
            return None
