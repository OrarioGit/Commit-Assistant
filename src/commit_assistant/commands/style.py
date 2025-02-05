import click
import os

from pathlib import Path

import click

def validate_options(ctx, param, value):
    """驗證 --path 和 --prompt 二選一存在"""
    if param.name == "path":
        ctx.params["path"] = value
    elif param.name == "prompt":
        ctx.params["prompt"] = value
    elif param.name == "style_name":
        ctx.params["style_name"] = value

    return value

def check_custom_dir_exist() -> Path:
    """
        確保 custom 目錄存在

        Returns:
            custom_dir (Path): custom 目錄路徑
    """
    custom_dir = Path(__file__).parent.parent / "prompts/custom"

    if not custom_dir.exists():
        os.makedirs(custom_dir)
    
    return custom_dir

@click.group()
def style():
    """
        style 指令
    """
    pass

@style.command()
@click.option("--path", type=click.Path(exists=True), help="Provide a file or directory path.", callback=validate_options)
@click.option("--prompt", type=str, help="Provide a prompt content.", callback=validate_options)
@click.option("--style-name", type=str, help="Provide a style name.", callback=validate_options)
@click.pass_context
def create(ctx, path: str = None, prompt: str = None, style_name: str = None):
    """
    新增自定義 prompt style
    若 path 和 prompt 同時存在，則只使用 path

    Args:
        path (str, optional): prompt 檔案路徑, 與 style 二選一.
        prompt (str, optional): prompt 內容, 與 path 二選一.
    """
    if prompt and not style_name:
        raise click.UsageError("If --prompt is provided, --style-name must be provided.")

    if path:
        # 讀取檔案內容
        with open(path, "r", encoding="utf-8") as f:
            prompt = f.read()
            
            # 將檔案內容寫入 custom 目錄
            # 寫入前檢查 custom 目錄是否存在
            custom_dir = check_custom_dir_exist()
            
            # 寫入檔案
            custom_file_path = custom_dir / f"{Path(path).stem}.txt"

            with open(custom_file_path, "w", encoding="utf-8") as f:
                f.write(prompt)
    elif prompt:
        # 將檔案內容寫入 custom 目錄
        # 寫入前檢查 custom 目錄是否存在
        custom_dir = check_custom_dir_exist()
        
        # 寫入檔案
        custom_file_path = custom_dir / f"{style_name}.txt"

        with open(custom_file_path, "w", encoding="utf-8") as f:
            f.write(prompt)

@style.command()
@click.option("--style-name", type=str, help="Provide a style name.", callback=validate_options)
def delete(style_name: str):
    """
    移除自定義 prompt style

    Args:
        style_name (str): 要移除的 style 名稱
    """
    custom_dir = check_custom_dir_exist()
    custom_file_path = custom_dir / f"{style_name}.txt"

    if custom_file_path.exists():
        os.remove(custom_file_path)
        click.echo(f"Style {style_name} removed.")
    else:
        click.echo(f"Style {style_name} not found.")

@style.command()
def list():
    """
    列出所有支援的風格
    """
    default_dir = Path(__file__).parent.parent / "prompts/default"
    custom_dir = Path(__file__).parent.parent / "prompts/custom"

    default_styles = [file.stem for file in default_dir.glob("*.txt")]
    custom_styles = [file.stem for file in custom_dir.glob("*.txt")]

    click.echo("Default Styles:")
    for style in default_styles:
        click.echo(f"  - {style}")

    click.echo("Custom Styles:")
    for style in custom_styles:
        click.echo(f"  - {style} {'[apply]' if style in default_styles else ''}")
