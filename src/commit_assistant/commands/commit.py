import os
import sys
from typing import List, Optional

import click
import questionary
from google.generativeai.types import GenerateContentResponse

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.enums.commit_style import CommitStyle
from commit_assistant.enums.exit_code import ExitCode
from commit_assistant.enums.user_choices import UserChoices
from commit_assistant.utils.config_utils import load_config
from commit_assistant.utils.console_utils import console, display_ai_message, loading_spinner
from commit_assistant.utils.git_utils import GitCommandRunner


class EnhancedCommitGenerator(BaseGeminiAIGenerator):
    def generate_structured_message(
        self, changed_files: List[str], diff_content: str
    ) -> Optional[GenerateContentResponse]:
        """生成結構化的commit message

        Args:
            changed_files (List[str]): 修改的文件列表
            diff_content (str): git diff內容

        Returns:
            GenerateContentResponse | None: 生成的commit message
        """

        # 獲取指定風格的prompt
        use_style = os.getenv("COMMIT_STYLE", CommitStyle.CONVENTIONAL.value)
        prompt = self.style_manager.get_prompt(use_style, changed_files, diff_content)

        console.print(f"[cyan]生成 commit message 使用 <{use_style}> 風格 [/cyan]")

        try:
            return self._generate_content(prompt)
        except Exception as e:
            console.print("[red]生成commit message時發生錯誤: [/red]")
            console.print(f"[red]{e}[/red]")
            return None


def get_user_choice(choices: List[str]) -> str:
    """
    提供簡單的數字選單供使用者選擇

    Args:
        choices (List[str]): 選項列表

    Returns:
        str: 使用者選擇的選項
    """
    console.print("\n請選擇操作：")
    for i, choice in enumerate(choices, 1):
        console.print(f"[cyan]{i}.[/cyan] {choice}")

    while True:
        try:
            selection = input("\n請輸入數字選項 (1-{}): ".format(len(choices)))
            idx = int(selection) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
            console.print("[red]無效的選擇，請重試[/red]")
        except ValueError:
            console.print("[red]請輸入有效的數字[/red]")


def edit_commit_message(initial_message: str = "") -> tuple[str, bool]:
    """
    使用 questionary 提供互動式編輯功能

    Returns:
        tuple[str, bool]: (編輯後的訊息, 是否確認提交)
    """
    while True:
        message = questionary.text(
            "請輸入/編輯 commit message：",
            default=initial_message,
            multiline=True,  # 允許多行輸入
        ).ask()

        if message is None:  # 使用者按了 Ctrl+C
            return "", False

        # 確認訊息
        console.print("\n您輸入的 commit message：")
        console.print("=" * 50)
        console.print(f"[blue]{message}[/blue]")
        console.print("=" * 50)

        if questionary.confirm("確認使用這個 message？").ask():
            return message, True
        else:
            initial_message = message  # 使用上次輸入的內容繼續編輯


def update_commit_message(commit_msg_file: str, ai_message: str) -> int:
    """更新 commit message 檔案

    Args:
        commit_msg_file (str): commit message 檔案路徑
        ai_message (str): 新的 commit message 內容

    Returns:
        int: ExitCode 的值
    """
    try:
        # 顯示 AI 生成的建議
        display_ai_message(ai_message)

        choices = [
            UserChoices.USE_AI_MESSAGE.value,
            UserChoices.EDIT_AI_MESSAGE.value,
            UserChoices.CANCEL_OPERATION.value,
        ]

        # 詢問使用者要如何處理
        choice = get_user_choice(choices)

        # 如果是使用者直接ctrl+c取消
        if choice is None or choice == UserChoices.CANCEL_OPERATION.value:
            console.print("[yellow]Commit 已取消[/yellow]")
            return ExitCode.CANCEL.value

        final_message = ""

        if choice == UserChoices.USE_AI_MESSAGE.value:
            final_message = ai_message
        elif choice == UserChoices.EDIT_AI_MESSAGE.value:
            edited_message, confirmed = edit_commit_message(ai_message)
            if not confirmed:
                console.print("[yellow]Commit 已取消[/yellow]")
                return ExitCode.CANCEL.value
            final_message = edited_message

        # 去除頭尾的 ``` 符號
        final_message = final_message.strip().strip("`")

        # 寫入 commit message
        with open(commit_msg_file, "w", encoding="utf-8") as f:
            f.write(final_message)

        console.print("[green]✓[/green] Commit message 已更新")
        return ExitCode.SUCCESS.value

    except Exception as e:
        console.print(f"[red]錯誤：{str(e)}[/red]")
        return ExitCode.ERROR.value


# @click.pass_context
@click.command()
@click.option(
    "--msg-file", "commit_msg_file", type=click.Path(), help="Path to commit message file", required=True
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to git repository",
    default=".",
)
def commit(commit_msg_file: str, repo_path: str) -> int:
    """
    透過AI生成commit message

    Args:
        commit_msg_file (str): git commit 要寫入的message檔案
        repo_path (str): git repository 路徑

    Returns:
        int: 成功返回0，否則返回其他數值
    """
    try:
        # 載入環境設定
        load_config(repo_path)

        # 判斷設定中是否要執行 commit assistant
        enable_commit_assistant = os.getenv("ENABLE_COMMIT_ASSISTANT", "true").lower() == "true"

        if not enable_commit_assistant:
            sys.exit(ExitCode.SUCCESS.value)

        git_command_runner = GitCommandRunner(repo_path)

        # 獲取變更資訊
        with loading_spinner("分析 Git 變更"):
            changed_files = git_command_runner.get_staged_files()
            if not changed_files:
                console.print("[yellow]沒有發現暫存的變更[/yellow]")
                sys.exit(ExitCode.CANCEL.value)

        # 獲取diff內容
        diff_content = git_command_runner.get_staged_diff()

        # 生成 commit message
        generator = EnhancedCommitGenerator()
        # 生成 commit message
        with loading_spinner("AI 生成 commit message"):
            response = generator.generate_structured_message(changed_files, diff_content)

        if not response:
            console.print("[red]✗[/red] 生成 commit message 失敗")
            sys.exit(ExitCode.ERROR)

        # 更新 commit message
        exit_code = update_commit_message(commit_msg_file, response.text)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]操作已取消[/yellow]")
        sys.exit(ExitCode.CANCEL)
    except Exception as e:
        console.print(f"[red]錯誤：{str(e)}[/red]")
        sys.exit(ExitCode.ERROR)
