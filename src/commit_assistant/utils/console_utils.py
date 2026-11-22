from contextlib import contextmanager
from typing import Iterator, List

from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from commit_assistant.core.commit_suggestion import CommitSuggestion, WarningLevel

console = Console()


@contextmanager
def loading_spinner(description: str = "處理中") -> Iterator[None]:
    """
    創建一個方便使用的進度動畫上下文管理器。

    Args:
        description (str): 要顯示的描述文字

    Examples:
        with loading_spinner("正在分析程式碼"):
            analyze_code()
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,  # 完成後自動移除進度顯示
    ) as progress:
        task = progress.add_task(description, total=None)
        try:
            yield None
        finally:
            progress.update(task, completed=True)


_WARNING_LEVEL_STYLES = {
    WarningLevel.HIGH: ("✗ 高", "bold red", "red"),
    WarningLevel.MEDIUM: ("! 中", "bold yellow", "yellow"),
    WarningLevel.LOW: ("· 低", "dim", "default"),
}


def display_commit_suggestion(suggestion: CommitSuggestion) -> None:
    """顯示 AI 產出的 commit 建議：commit message、注意事項、補充說明

    Args:
        suggestion (CommitSuggestion): AI 產出的建議
    """
    display_ai_message(suggestion.message)

    if suggestion.warnings:
        table = Table.grid(padding=(0, 2))
        table.add_column(no_wrap=True)
        table.add_column()

        for warning in suggestion.warnings:
            label, label_style, message_style = _WARNING_LEVEL_STYLES[warning.level]
            table.add_row(Text(label, style=label_style), Text(warning.message, style=message_style))

        # 只要有 high 等級的提醒，整個面板以紅框強調
        has_high = any(w.level == WarningLevel.HIGH for w in suggestion.warnings)
        border_style = "red" if has_high else "yellow"

        console.print(
            Panel(
                Padding(table, (0, 1)),
                title=Text("⚠ 注意事項", style=f"bold {border_style}"),
                title_align="left",
                border_style=border_style,
                expand=False,
            )
        )

    if suggestion.notes:
        console.print(
            Panel(
                Padding(Text(suggestion.notes, style="dim"), (0, 1)),
                title=Text("補充說明", style="dim"),
                title_align="left",
                border_style="bright_black",
                expand=False,
            )
        )

    if suggestion.warnings or suggestion.notes:
        console.print()


def display_ai_message(ai_message: str) -> None:
    """使用多層次 panel 來顯示 AI 生成的 commit message"""
    # 創建標題
    title = Text("💡 AI Commit Suggestion", style="bold cyan")

    # 解析 message 的不同部分
    lines = ai_message.split("\n")
    header = lines[0] if lines else ""
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    # 創建要顯示的內容列表
    content_elements: List[Text] = [
        Text(header, style="bold blue"),
        Text(""),  # 空行
    ]

    # 如果有 body，則添加到列表中
    if body:
        content_elements.append(Text(body, style="blue"))

    # 創建 Group
    content = Group(*content_elements)

    # 創建帶有樣式的面板
    panel = Panel(Padding(content, (1, 2)), title=title, border_style="cyan", expand=False, highlight=True)

    console.print()
    console.print(Panel(panel, border_style="white", padding=(1, 2), expand=False))
    console.print()
