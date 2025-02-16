import sys
from pathlib import Path

import click

from commit_assistant.utils.console_utils import console
from commit_assistant.utils.installation_manager import InstallationManager
from commit_assistant.utils.update_utils import UpdateManager


def _update_all_repos() -> None:
    """更新所有專案底下的相關檔案"""
    console.print("[yellow]開始更新所有專案底下的相關檔案...[/yellow]")

    # 取得所有已經安裝過的專案
    installation_manager = InstallationManager()
    installations = installation_manager.get_all_installations()

    if not installations:
        console.print("[yellow]沒有找到任何已安裝的專案[/yellow]")
        return

    console.print(f"[yellow][bold]找到 {len(installations)} 個已安裝的專案[/bold][/yellow]")
    for installation in installations:
        repo_path = Path(installation["repo_path"])

        console.print(f"[yellow]開始更新專案: {repo_path}...[/yellow]")

        try:
            update_manager = UpdateManager(repo_path)
            update_manager.update()
        except Exception as e:
            console.print(f"[red]更新失敗{repo_path}，錯誤: {str(e)}[/red]")
            continue

        # 更新成功，紀錄該repo的安裝訊息
        installation_manager.add_installation(repo_path)

    console.print("[green]所有專案底下的相關檔案更新完成!![/green]\n")


def _update(repo_path: str) -> None:
    """更新專案底下的相關檔案"""
    console.print("[yellow]開始更新專案底下的相關檔案...[/yellow]")

    pure_repo_path = Path(repo_path)
    update_manager = UpdateManager(pure_repo_path)
    update_manager.update()

    installation_manager = InstallationManager()
    installation_manager.add_installation(pure_repo_path)  # 更新成功，紀錄該repo的安裝訊息

    console.print("[green]專案底下的相關檔案更新完成!![/green]\n")


@click.group(invoke_without_command=True)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Path to git repository",
)
@click.option(
    "--all-repo",
    is_flag=True,
    help="Update all repositories",
    default=False,
)
@click.pass_context
def update(ctx: click.Context, repo_path: str, all_repo: bool) -> None:
    """將專案底下的hook與config等相關檔案更新至最新版本"""
    try:
        if all_repo:
            _update_all_repos()
        else:
            _update(repo_path)
        sys.exit(0)

    except Exception as e:
        console.print(f"[red]更新失敗，錯誤: {str(e)}[/red]")
        sys.exit(1)
