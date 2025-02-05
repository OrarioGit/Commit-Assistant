import os
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from commit_assistant.utils.console_utils import console
from commit_assistant.utils.git_utils import CommitStyleManager


class BaseGeminiAIGenerator:
    """建立一個Gemini Ai Generator的基類"""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key is None:
            console.print("[yellow]檢測到尚未設定 Gemini api key [/yellow]")
            raise ValueError("請先執行commit-assistant config setup設定API金鑰")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GENERATIVE_MODEL", "gemini-2.0-flash-exp"))
        self.style_manager = CommitStyleManager()

    def _generate_content(self, prompt: str) -> Optional[GenerateContentResponse]:
        try:
            response = self.model.generate_content(prompt)
            return response
        except Exception as e:
            console.print("[red]生成內容時發生錯誤: [/red]")
            console.print(f"[red]{e}[/red]")
            return None
