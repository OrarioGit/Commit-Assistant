import click
import os
import pyperclip
import sys
from datetime import datetime
from typing import List, Union

import google.generativeai as genai
import questionary
from google.generativeai.types import GenerateContentResponse

from commit_assistant.enums.exit_code import ExitCode
from commit_assistant.utils.console_utils import console, display_ai_message
from commit_assistant.utils.config_utils import load_config
from commit_assistant.utils.git_utils import CommitStyleManager, GitCommandRunner

class CommitSummaryGenerator:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")

        if api_key is None:
            console.print("[yellow]檢測到尚未設定 Gemini api key [/yellow]")

            raise ValueError("請先執行commit-assistant config setup設定API金鑰")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(os.getenv("GENERATIVE_MODEL", "gemini-2.0-flash-exp"))

        self.style_manager = CommitStyleManager()

    def generate_commit_summary(self, commit_message: str) -> str:
        """生成 commit message 的摘要

        Args:
            commit_message (str): commit message 內容

        Returns:
            str: commit message 摘要
        """
        console.print(f"[cyan]正在進行 commit 摘要 [/cyan]")

        try:
            prompt = f"""
                請使用繁體中文根據以下的 commit message 生成 commit 簡短摘要。
                摘要時請用純文字與換行字元，不要包含任何表情符號或特殊符號。
                文字中不要包含 commit hash

                Commit Message:
                {commit_message}
            """

            response = self.model.generate_content(prompt)

            if not response:
                console.print("[red]✗[/red] 生成 commit message 失敗")
                sys.exit(ExitCode.ERROR)

            return response
        except Exception as e:
            console.print("[red]生成commit 摘要時發生錯誤: [/red]")
            console.print(f"[red]{e}[/red]")
            return None

@click.command()
@click.option("--start-from", "start_from", help="Please provide the commit messages starting from which date.", default=None)
@click.option("--end-to", "end_to", help="Please provide the commit messages ending at which date.", default=None)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to git repository",
    default=".",
)
def summary(start_from: str, end_to: str, repo_path: str) -> None:
    """
        將 commit 訊息進行摘要

        Args:
            start_from (str): 起始日期, 預設使用當日 00:00:00
            end_to (str): 結束日期, 預設使用當日 23:59:59
    """
    # 載入環境設定
    load_config(repo_path)
    
    start_from = start_from or datetime.now().strftime("%Y-%m-%d 00:00:00")
    end_to = end_to or datetime.now().strftime("%Y-%m-%d 23:59:59")

    git_command_runner = GitCommandRunner(repo_path)

    # 獲取 commit message
    commit_message = git_command_runner.get_commit_message(start_from, end_to)
    
    # 透過 AI 進行摘要
    summary_generator = CommitSummaryGenerator()
    summary = summary_generator.generate_commit_summary(commit_message)

    display_ai_message(summary.text)

    # 將摘要複製到剪貼簿
    pyperclip.copy(summary.text)
    console.log("[green]✓[/green] 摘要已複製到剪貼簿")