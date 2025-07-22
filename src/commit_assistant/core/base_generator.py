"""Gemini AI 生成器的基礎類別模組

此模組提供與 Gemini AI API 互動的基礎功能，作為所有 AI 生成器的父類別。
主要功能包括：
1. Gemini API 的初始化與設定
2. 基礎模型實例的建立
3. 共用的 commit style 管理

典型使用方式:
```python
class CustomGenerator(BaseGeminiAIGenerator):
    def generate_content(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return self._process_response(response)
```

屬性:
    model: Gemini AI 生成模型實例
    style_manager: Commit 風格管理器

環境變數:
    GEMINI_API_KEY: Gemini API 金鑰
    GENERATIVE_MODEL: 使用的模型名稱，預設為 "gemini-2.0-flash-exp"

錯誤處理:
    ValueError: 當未設定 API 金鑰時拋出
"""

import os
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from commit_assistant.utils.console_utils import console
from commit_assistant.utils.style_utils import CommitStyleManager


class BaseGeminiAIGenerator:
    """建立一個 Gemini Ai Generator 的基類"""

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key is None:
            console.print("[yellow] 檢測到尚未設定 Gemini api key [/yellow]")
            raise ValueError("請先執行 commit-assistant config setup 設定 API 金鑰")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GENERATIVE_MODEL", "gemini-2.0-flash-exp"))
        self.style_manager = CommitStyleManager()

    def _generate_content(self, prompt: str) -> Optional[GenerateContentResponse]:
        try:
            response = self.model.generate_content(prompt)
            return response
        except Exception as e:
            console.print("[red] 生成內容時發生錯誤：[/red]")
            console.print(f"[red]{e}[/red]")
            return None
