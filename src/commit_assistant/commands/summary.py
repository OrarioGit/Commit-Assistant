import sys
from datetime import datetime, timedelta
from typing import Optional

import click
import pyperclip
from google.generativeai.types import GenerateContentResponse

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.enums.exit_code import ExitCode
from commit_assistant.utils.config_utils import load_config
from commit_assistant.utils.console_utils import console, display_ai_message, loading_spinner
from commit_assistant.utils.git_utils import GitCommandRunner


class CommitSummaryGenerator(BaseGeminiAIGenerator):
    def generate_commit_summary(
        self, commit_message: str, start_dt: datetime, end_dt: datetime
    ) -> Optional[GenerateContentResponse]:
        """生成 commit message 的摘要

        Args:
            commit_message (str): commit message 內容

        Returns:
            str: commit message 摘要
        """
        start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

        console.print(f"[cyan] 摘要期間 {start_str} ~ {end_str} [/cyan]")

        try:
            prompt = f"""請根據以下的 commit message 生成繁體中文摘要：
                1. 使用「•」作為條列符號
                2. 每個項目需簡短扼要說明修改內容
                3. 僅包含最重要的前個項目，最多不超過10個項目
                4. 不使用表情符號或特殊符號
                5. 不包含 commit hash

                Commit Message:
                {commit_message}

                輸出格式範例：
                - 新增用戶註冊功能
                - 加入電子郵件驗證
                - 修正登入頁面顯示問題
            """

            return self._generate_content(prompt)
        except Exception as e:
            console.print("[red]生成commit 摘要時發生錯誤: [/red]")
            console.print(f"[red]{e}[/red]")
            return None


def _parse_date(date_str: Optional[str]) -> datetime:
    """解析日期字串

    Args:
        date_str (Optional[str]): 使用者輸入的日期字串

    Raises:
        click.BadParameter: _description_

    Returns:
        datetime: 解析後的日期
    """

    if date_str is None:
        return datetime.now()

    # 針對使用者輸入的特殊日期進行處理
    # 例如: today, yesterday, 7d
    if date_str == "today":
        return datetime.now()
    elif date_str == "yesterday":
        return datetime.now() - timedelta(days=1)
    elif date_str.endswith("d"):
        try:
            days = int(date_str[:-1])
            return datetime.now() - timedelta(days=days)
        except ValueError:
            pass

    # 如果不是上述的特殊日期，則進行日期格式解析
    # 以下是支援的日期格式
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y%m%d",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise click.BadParameter(f"Unsupported date format: {date_str}")


@click.command()
@click.option(
    "--start-from",
    "start_from",
    help="Starting date. Supports: 'YYYY-MM-DD', 'today', 'yesterday', '7d (7 days ago)', or flexible formats",
    default=None,
)
@click.option("--end-to", "end_to", help="Ending date. Same format as start-from", default=None)
@click.option(
    "--author",
    "author",
    help="""Filters commit history to show only commits where the author's name matches the specified regular expression.
For example: `--author="^Alice"` will match commits authored by names starting with "Alice".
""",
    default=None,
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to git repository",
    default=".",
)
def summary(start_from: Optional[str], end_to: Optional[str], author: Optional[str], repo_path: str) -> None:
    """將 commit 訊息進行摘要

    Args:
        start_from (str): 起始日期, 預設使用當日 00:00:00
        end_to (str): 結束日期, 預設使用當日 23:59:59
        author (str): 作者名稱, 預設為 None(不篩選作者)
        repo_path (str): git repository 路徑
    """
    # 載入環境設定
    load_config(repo_path)

    start_dt = _parse_date(start_from)
    end_dt = _parse_date(end_to)

    # 如果使用者沒有指定日期，則預設為當日
    # 起始日期為 當日的00:00:00, 結束日期為 當日的23:59:59
    if start_from is None:
        start_dt = start_dt.replace(hour=0, minute=0, second=0)
    if end_to is None:
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

    git_command_runner = GitCommandRunner(repo_path)

    # 獲取該段時間內的commit message
    commit_message = git_command_runner.get_commits_in_date_range(start_dt, end_dt, author)
    if not commit_message:
        console.print(f"[yellow]{start_dt} ~ {end_dt} 範圍內沒有找到符合條件的 commit message[/yellow]")
        sys.exit(ExitCode.CANCEL)

    with loading_spinner("正在產生commit 摘要"):
        # 透過 AI 進行摘要
        summary_generator = CommitSummaryGenerator()
        summary = summary_generator.generate_commit_summary(commit_message, start_dt, end_dt)

    if summary is None:
        console.print("[red]✗[/red] 摘要生成失敗")
        sys.exit(ExitCode.ERROR)

    # 將摘要複製到剪貼簿
    try:
        pyperclip.copy(summary.text)
        console.print("[green]✓[/green] 摘要已複製到剪貼簿")

        display_ai_message(summary.text)
    except Exception:
        console.print("[red]✗[/red] 無法複製摘要到剪貼簿, 請確認操作環境是否支援剪貼簿操作")
        console.print("摘要內容如下:")
        console.print(summary.text)

    sys.exit(ExitCode.SUCCESS)
