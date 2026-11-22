"""AI 生成器的基礎類別模組

支援 Gemini API 與 Claude CLI 兩種 provider。
透過 USE_CLAUDE_CLI=true 啟用 Claude CLI 模式（不需要 API key，使用已經登入的 Claude Code）。
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from commit_assistant.core.commit_suggestion import parse_json_object
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.enums.default_value import DefaultValue
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.style_utils import CommitStyleManager

# 已棄用的 Gemini 模型與官方建議的替代模型
# 參考 https://aistudio.google.com/docs/deprecations
DEPRECATED_GEMINI_MODELS = {
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-pro": "gemini-3.8-flash",
    "gemini-2.0-flash": "gemini-3.6-flash",
    "gemini-2.0-flash-001": "gemini-3.6-flash",
}


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

        if self._use_claude_cli:
            self.model = (
                os.getenv(ConfigKey.CLAUDE_CLI_MODEL.value) or DefaultValue.DEFAULT_CLAUDE_CLI_MODEL.value
            )
            self.effort = (
                os.getenv(ConfigKey.CLAUDE_CLI_EFFORT.value) or DefaultValue.DEFAULT_CLAUDE_CLI_EFFORT.value
            )
        else:
            self.model = os.getenv(ConfigKey.USE_MODEL.value) or DefaultValue.DEFAULT_MODEL.value
            self._warn_deprecated_model()

        self.style_manager = CommitStyleManager()

    def _warn_deprecated_model(self) -> None:
        """使用已棄用的 Gemini 模型時，提醒使用者更換"""
        replacement = DEPRECATED_GEMINI_MODELS.get(self.model)
        if replacement is None:
            return

        console.print(
            f"[yellow] 模型 {self.model} 已被 Google 棄用，"
            f"建議將設定檔中的 {ConfigKey.USE_MODEL.value} 改為 {replacement} [/yellow]"
        )

    @property
    def provider_label(self) -> str:
        """顯示給使用者看的 provider 與模型名稱"""
        if self._use_claude_cli:
            return f"Claude CLI <{self.model}>"
        return f"Gemini <{self.model}>"

    def _run_claude_cli(self, prompt: str, extra_args: Optional[List[str]] = None) -> Optional[str]:
        """呼叫 claude -p 並回傳 stdout

        - 透過 stdin 傳入 prompt，避免 prompt 過長超出命令列長度限制
        - 關閉所有工具，避免 Claude 自行讀檔或執行指令，拖慢速度並產生多餘的解釋
        - 不保存 session，避免每次 commit 都在 Claude Code 的歷史中留下紀錄
        - 不載入 MCP server 與使用者設定，縮短啟動時間

        Args:
            prompt (str): 要傳給 Claude 的 prompt
            extra_args (Optional[List[str]]): 額外的 CLI 參數

        Returns:
            Optional[str]: Claude CLI 的 stdout，失敗時回傳 None
        """
        # 使用完整路徑，讓 Windows 上透過 npm 安裝的 claude.cmd 也能以參數列表方式執行
        claude_path = shutil.which("claude") or "claude"

        cmd = [
            claude_path,
            "-p",
            "--model",
            self.model,
            # 寫 commit message 不需要深度推理，預設使用低 effort 以節省用量
            "--effort",
            self.effort,
            "--tools",
            "",
            "--no-session-persistence",
            # 不載入使用者的 MCP server、設定與 slash command，省下每次約 2～3 秒的啟動時間
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--disable-slash-commands",
        ]
        cmd.extend(extra_args or [])

        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            console.print(f"[red]{result.stderr or result.stdout}[/red]")
            return None

        return result.stdout.strip()

    def _generate_content(self, prompt: str) -> Optional[str]:
        """以純文字形式生成內容

        Args:
            prompt (str): prompt 內容

        Returns:
            Optional[str]: 生成的文字，失敗時回傳 None
        """
        try:
            if self._use_claude_cli:
                return self._run_claude_cli(prompt)

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            console.print("[red] 生成內容時發生錯誤：[/red]")
            console.print(f"[red]{e}[/red]")
            return None

    def _generate_structured(
        self, prompt: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """以結構化（JSON Schema）形式生成內容

        Args:
            prompt (str): prompt 內容
            system_prompt (str): 系統提示詞，用來約束模型的角色與輸出格式
            schema (Dict[str, Any]): 回傳資料需符合的 JSON Schema

        Returns:
            Optional[Dict[str, Any]]: 符合 schema 的資料，失敗時回傳 None
        """
        try:
            if self._use_claude_cli:
                return self._generate_structured_with_claude_cli(prompt, system_prompt, schema)
            return self._generate_structured_with_gemini(prompt, system_prompt, schema)
        except Exception as e:
            console.print("[red] 生成內容時發生錯誤：[/red]")
            console.print(f"[red]{e}[/red]")
            return None

    def _generate_structured_with_claude_cli(
        self, prompt: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        # system prompt 含有換行，直接放在命令列參數中會在 Windows 的 .cmd 被截斷，因此改用檔案傳遞
        with tempfile.TemporaryDirectory() as temp_dir:
            system_prompt_file = Path(temp_dir) / "system_prompt.txt"
            system_prompt_file.write_text(system_prompt, encoding="utf-8")

            stdout = self._run_claude_cli(
                prompt,
                [
                    "--system-prompt-file",
                    str(system_prompt_file),
                    "--output-format",
                    "json",
                    "--json-schema",
                    json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
                ],
            )

        if stdout is None:
            return None

        result = json.loads(stdout)

        # 結構化輸出放在 structured_output，若沒有則嘗試從 result 文字中解析
        structured = result.get("structured_output")
        if isinstance(structured, dict):
            return structured

        return parse_json_object(str(result.get("result", "")))

    def _generate_structured_with_gemini(
        self, prompt: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_json_schema=schema,
            ),
        )

        return parse_json_object(response.text or "")
