import sys
from pathlib import Path

import click

from commit_assistant.utils.config_utils import install_config
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.hook_manager import HookManager


@click.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Path to git repository",
)
def install(repo_path: str) -> None:
    """安裝 commit-assistant hook 到 git repository中
    1. 複製 hook 模板到 .git/hooks/prepare-commit-msg
    2. 複製 config 模板到 .commit-assistant-config
    """
    try:
        pure_repo_path = Path(repo_path)
        hook_manager = HookManager(pure_repo_path)

        # 讀取 hook 模板
        package_dir = Path(__file__).parent.parent
        hook_template = package_dir / "resources" / "hooks" / "prepare-commit-msg"
        hook_content = hook_template.read_text(encoding="utf-8")

        # 安裝 hook
        hook_manager.install_hook(hook_content)
        console.print("[green]commit-assistant hook 安裝成功[/green]")

        # 安裝 config
        install_config(repo_path)

        sys.exit(0)

    except Exception as e:
        console.print(f"[red]安裝失敗，錯誤: {str(e)}[/red]")
        sys.exit(1)
