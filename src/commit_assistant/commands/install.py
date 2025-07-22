import sys
from pathlib import Path

import click

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.config_utils import install_config
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.hook_manager import HookManager
from commit_assistant.utils.installation_manager import InstallationManager


@click.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Path to git repository",
)
def install(repo_path: str) -> None:
    """
    安裝 commit-assistant hook 到 git repository 中

    1. 複製 hook 模板到 .git/hooks/prepare-commit-msg
    2. 複製 config 模板到 .commit-assistant-config
    """
    try:
        pure_repo_path = Path(repo_path)
        hook_manager = HookManager(pure_repo_path)

        # 讀取 hook 模板
        hook_template = ProjectPaths.HOOKS_DIR / ProjectInfo.HOOK_TEMPLATE_NAME
        hook_content = hook_template.read_text(encoding="utf-8")

        # 安裝 hook
        hook_manager.install_hook(hook_content)
        console.print("[green]commit-assistant hook 安裝成功 [/green]")

        # 安裝 config
        install_config(repo_path)

        # 紀錄安裝訊息
        installation_manager = InstallationManager()
        installation_manager.add_installation(pure_repo_path)

        sys.exit(0)

    except Exception as e:
        console.print(f"[red] 安裝失敗，錯誤：{str(e)}[/red]")
        sys.exit(1)
