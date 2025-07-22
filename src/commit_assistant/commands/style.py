import shutil
from pathlib import Path
from typing import Optional

import click
import questionary
import yaml
from rich.text import Text

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import StyleScope
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.style_utils import CommitStyleManager, StyleImporter


def _validate_yaml(ctx: Optional[click.Context], param: Optional[click.Parameter], value: str) -> Path:
    if not value.endswith(".yaml"):
        raise click.BadParameter("檔案必須是 .yaml 格式")
    return Path(value)


def _print_all_styles(dir: Path) -> None:
    """讀取該目錄下的所有 style 檔案並列印"""
    found_file = False

    for yaml_file in dir.glob("*.yaml"):
        found_file = True
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                style_name = yaml_file.stem

                style_data = yaml.safe_load(f)
                description = style_data.get("description", "無描述")

                # 使用 rich Text 來避免英文的描述文字無法被 rich 正確解析
                text = Text()
                text.append(f"  - {style_name}  ")
                text.append(f"[{description}]", style="blue")
                console.print(text)
        except Exception:
            console.print(f"  - {yaml_file.stem} [red] 讀取失敗 [/red]")

    if not found_file:
        console.print("  - [red] 尚無可用的 style[/red]")


@click.group()
def style() -> None:
    """管理 commit message 使用的風格"""


@style.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to git repository",
    default=".",
)
def list(repo_path: str) -> None:
    """列出所有可用的風格"""
    console.print("可用的風格：")

    # 列出系統內建的 style
    console.print(f"[cyan]{StyleScope.SYSTEM.value}風格:[/cyan]")
    system_style_dir = ProjectPaths.STYLE_DIR / "system"
    if system_style_dir.exists():
        _print_all_styles(system_style_dir)

    # 使用者全域設定的 style
    console.print(f"[green]{StyleScope.GLOBAL.value}風格:[/green]")
    global_style_dir = ProjectPaths.STYLE_DIR / "global"
    if global_style_dir.exists():
        _print_all_styles(global_style_dir)

    # 專案內設定的 style
    console.print(f"[yellow]{StyleScope.PROJECT.value}風格:[/yellow]")
    project_style_dir = Path(repo_path).absolute() / ProjectInfo.REPO_ASSISTANT_DIR / "style"
    if project_style_dir.exists():
        _print_all_styles(project_style_dir)
    else:
        console.print("  - [red] 尚無可用的 style[/red]")


@style.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="export style to specific directory",
    default=".",
)
def template(output: str) -> None:
    """匯出風格撰寫模板，提供使用者參考"""
    template_path = ProjectPaths.STYLE_DIR / ProjectInfo.STYLE_TEMPLATE_NAME

    if not template_path.exists():
        console.print(f"[red] 失敗：找不到 style 模板檔案：{template_path}[/red]")
        return

    output_path = Path(output).absolute()

    # 將檔案複製到指定目錄
    output_file = output_path / ProjectInfo.STYLE_TEMPLATE_NAME
    shutil.copy(template_path, output_file)

    console.print(f"[green]✓ 成功將 style 模板複製到：{output_file}[/green]")


@style.command()
@click.argument("style-file", type=click.Path(exists=True), callback=_validate_yaml)
@click.option("--name", "-n", help="custom style name, if not set, use the file name")
@click.option("--global", "-g", "global_", is_flag=True, help="need import style as global template")
def add(style_file: str, name: Optional[str], global_: bool) -> None:
    """匯入風格 yaml 檔"""
    try:
        style_importer = StyleImporter(Path(style_file), name, global_)
        style_importer.start_import()
    except Exception as e:
        console.print(f"[red] 錯誤：{e}[/red]")


@style.command()
@click.argument("name")
def use(name: str) -> None:
    """設定當前專案要使用的風格名稱"""
    try:
        manager = CommitStyleManager()
        manager.set_project_commit_style(name)

        console.print(f"[green]✓ 成功設定當前專案使用 '{name}' 風格 [/green]")
    except ValueError as e:
        console.print(f"[red] 錯誤：{e}[/red]")


@style.command()
@click.argument("name")
@click.option("--global", "-g", "global_", is_flag=True, help="remove global style template")
def remove(name: str, global_: bool) -> None:
    """刪除指定的樣式模板"""
    # 決定要刪除的檔案路徑
    if global_:
        scope = StyleScope.GLOBAL.value
        style_folder_dir = ProjectPaths.STYLE_DIR / "global"
    else:
        scope = StyleScope.PROJECT.value
        style_folder_dir = Path(".").absolute() / ProjectInfo.REPO_ASSISTANT_DIR / "style"

    try:
        style_path = style_folder_dir / f"{name}.yaml"

        if not style_path.exists():
            console.print(
                f"[red] 錯誤：在 [blue][{scope}][/blue] 層級下，找不到名稱為 '{name}' 的風格模板 [/red]"
            )
            console.print("請確認風格名稱是否正確，或者指定的層級是否正確")
            return

        if questionary.confirm(f"確定要刪除 [{scope}] 風格 '{name}' 嗎？").ask():
            style_path.unlink()
            console.print(f"[green]✓ 成功刪除 {scope}風格 '{name}'[/green]")
        else:
            console.print("[yellow] 已取消刪除 [/yellow]")
    except Exception as e:
        console.print(f"[red] 錯誤：{e}[/red]")
