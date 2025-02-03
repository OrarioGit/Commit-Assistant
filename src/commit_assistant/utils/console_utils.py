from contextlib import contextmanager
from typing import Iterator, List

from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

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


def display_ai_message(ai_message: str) -> None:
    """使用多層次panel來顯示 AI 生成的 commit message"""
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
