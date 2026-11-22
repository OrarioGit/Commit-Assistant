import os
import sys
from typing import List, Optional

import click
import questionary

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.core.commit_suggestion import (
    COMMIT_SUGGESTION_SCHEMA,
    COMMIT_SUGGESTION_SYSTEM_PROMPT,
    CommitSuggestion,
    clean_commit_message,
)
from commit_assistant.enums.commit_style import CommitStyle
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.enums.exit_code import ExitCode
from commit_assistant.enums.user_choices import UserChoices
from commit_assistant.utils.command_runners import GitCommandRunner
from commit_assistant.utils.config_utils import load_config
from commit_assistant.utils.console_utils import console, display_commit_suggestion, loading_spinner
from commit_assistant.utils.environment_utils import is_interactive_environment

# 附帶給 AI 參考的未追蹤檔案數量上限，避免大量檔案塞滿 prompt
MAX_CONTEXT_FILES = 30


def _build_untracked_context(untracked_files: List[str]) -> str:
    """整理未被追蹤的新檔案，讓 AI 判斷 staged 的程式碼是否引用了忘記 git add 的檔案

    只提供未追蹤的檔案，不提供「已修改但未暫存」的檔案：
    使用者分段 commit 時本來就會刻意留下這些檔案，提供給 AI 只會產生大量無用的提醒。

    Args:
        untracked_files (List[str]): 未被追蹤的檔案

    Returns:
        str: 附加在 prompt 後方的說明，沒有任何檔案時回傳空字串
    """
    if not untracked_files:
        return ""

    lines = [f"- {file}" for file in untracked_files[:MAX_CONTEXT_FILES]]
    if len(untracked_files) > MAX_CONTEXT_FILES:
        lines.append(f"- ...（另有 {len(untracked_files) - MAX_CONTEXT_FILES} 個檔案）")

    return (
        "\n\n以下是尚未被 git 追蹤的新檔案，只用來判斷 staged 的程式碼是否引用了忘記 git add 的檔案，"
        "不要寫進 commit message：\n" + "\n".join(lines)
    )


class EnhancedCommitGenerator(BaseGeminiAIGenerator):
    def generate_structured_message(
        self,
        changed_files: List[str],
        diff_content: str,
        untracked_files: Optional[List[str]] = None,
    ) -> Optional[CommitSuggestion]:
        """生成結構化的 commit 建議

        Args:
            changed_files (List[str]): 修改的文件列表
            diff_content (str): git diff 內容
            untracked_files (Optional[List[str]]): 未被追蹤的文件列表

        Returns:
            CommitSuggestion | None: 生成的 commit 建議
        """

        # 獲取指定風格的 prompt
        use_style = os.getenv(ConfigKey.COMMIT_STYLE.value, CommitStyle.CONVENTIONAL.value)
        prompt = self.style_manager.get_prompt(use_style, changed_files, diff_content)
        prompt += _build_untracked_context(untracked_files or [])

        console.print(
            f"[cyan] 生成 commit message 使用 <{use_style}> 風格，採用 {self.provider_label} [/cyan]"
        )

        try:
            data = self._generate_structured(
                prompt, COMMIT_SUGGESTION_SYSTEM_PROMPT, COMMIT_SUGGESTION_SCHEMA
            )
            if data is not None:
                try:
                    return CommitSuggestion.from_dict(data)
                except ValueError:
                    pass

            # 結構化輸出失敗時退回純文字模式，至少讓使用者拿到 commit message
            console.print("[yellow] 無法取得結構化結果，改用純文字模式重新生成 [/yellow]")
            text = self._generate_content(prompt)
            if not text:
                return None
            return CommitSuggestion.from_text(text)
        except Exception as e:
            console.print("[red] 生成 commit message 時發生錯誤：[/red]")
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
            console.print("[red] 無效的選擇，請重試 [/red]")
        except ValueError:
            console.print("[red] 請輸入有效的數字 [/red]")


def edit_commit_message(initial_message: str = "") -> tuple[str, bool]:
    """
    使用 questionary 提供互動式編輯功能

    Returns:
        tuple[str, bool]: (編輯後的訊息，是否確認提交)
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


def update_commit_message(commit_msg_file: str, suggestion: CommitSuggestion) -> tuple[int, bool]:
    """更新 commit message 檔案

    Args:
        commit_msg_file (str): commit message 檔案路徑
        suggestion (CommitSuggestion): AI 產出的 commit 建議

    Returns:
        tuple[int, bool]: (ExitCode 的值，是否需要重新產生 commit message)
    """
    need_regenerate = False

    try:
        # 顯示 AI 生成的建議
        display_commit_suggestion(suggestion)
        ai_message = suggestion.message

        choices = [
            UserChoices.USE_AI_MESSAGE.value,
            UserChoices.EDIT_AI_MESSAGE.value,
            UserChoices.REGENERATE_AI_MESSAGE.value,
            UserChoices.CANCEL_OPERATION.value,
        ]

        # 詢問使用者要如何處理
        choice = get_user_choice(choices)

        # 如果是使用者直接 ctrl+c 取消
        if choice is None or choice == UserChoices.CANCEL_OPERATION.value:
            console.print("[yellow]Commit 已取消 [/yellow]")
            return ExitCode.CANCEL.value, need_regenerate

        # 如果使用者選擇重新生成
        if choice == UserChoices.REGENERATE_AI_MESSAGE.value:
            need_regenerate = True
            return ExitCode.CANCEL.value, need_regenerate

        final_message = ""

        if choice == UserChoices.USE_AI_MESSAGE.value:
            final_message = ai_message
        elif choice == UserChoices.EDIT_AI_MESSAGE.value:
            edited_message, confirmed = edit_commit_message(ai_message)
            if not confirmed:
                console.print("[yellow]Commit 已取消 [/yellow]")
                return ExitCode.CANCEL.value, need_regenerate
            final_message = edited_message
        else:
            console.print("[red] 選項錯誤，無法使用的選項 [/red]")
            return ExitCode.ERROR.value, need_regenerate

        # 去除頭尾的 ``` 符號
        final_message = clean_commit_message(final_message)

        # 寫入 commit message
        with open(commit_msg_file, "w", encoding="utf-8") as f:
            f.write(final_message)

        console.print("[green]✓[/green] Commit message 已更新")
        return ExitCode.SUCCESS.value, need_regenerate

    except Exception as e:
        console.print(f"[red] 錯誤：{str(e)}[/red]")
        return ExitCode.ERROR.value, False


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
    透過 AI 生成 commit message

    Args:
        commit_msg_file (str): git commit 要寫入的 message 檔案
        repo_path (str): git repository 路徑

    Returns:
        int: 成功返回 0，否則返回其他數值
    """
    try:
        # 載入環境設定
        load_config(repo_path)

        # 判斷設定中是否要執行 commit assistant
        enable_commit_assistant = os.getenv("ENABLE_COMMIT_ASSISTANT", "true").lower() == "true"

        if not enable_commit_assistant:
            sys.exit(ExitCode.SUCCESS.value)

        # 由 AI agent 或沒有終端機的環境發起時不介入，保留呼叫端自己的 commit message
        if not is_interactive_environment():
            sys.exit(ExitCode.SUCCESS.value)

        git_command_runner = GitCommandRunner(repo_path)

        # 獲取變更資訊
        with loading_spinner("分析 Git 變更"):
            changed_files = git_command_runner.get_staged_files()
            if not changed_files:
                console.print("[yellow] 沒有發現暫存的變更 [/yellow]")
                sys.exit(ExitCode.CANCEL.value)

        # 獲取 diff 內容，以及尚未被追蹤的新檔案
        diff_content = git_command_runner.get_staged_diff()
        untracked_files = git_command_runner.get_untracked_files()

        # 生成 commit message
        generator = EnhancedCommitGenerator()

        while True:
            # 生成 commit message
            with loading_spinner("AI 生成 commit message"):
                response = generator.generate_structured_message(changed_files, diff_content, untracked_files)

            if not response:
                console.print("[red]✗[/red] 生成 commit message 失敗")
                sys.exit(ExitCode.ERROR)

            # 更新 commit message
            exit_code, need_regenerate = update_commit_message(commit_msg_file, response)

            if not need_regenerate:
                sys.exit(exit_code)

            console.print("[blue] 重新生成 commit message... [/blue]")
    except KeyboardInterrupt:
        console.print("\n[yellow] 操作已取消 [/yellow]")
        sys.exit(ExitCode.CANCEL)
    except Exception as e:
        console.print(f"[red] 錯誤：{str(e)}[/red]")
        sys.exit(ExitCode.ERROR)
