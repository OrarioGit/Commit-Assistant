import click

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.command_runners import CommandRunner
from commit_assistant.utils.console_utils import console
from commit_assistant.utils.upgrade_checker import UpgradeChecker


def _upgrade(yes: bool) -> None:
    """更新 commit assistant 至最新版本"""
    # 先檢查是否真的需要更新
    checker = UpgradeChecker()

    newest_version = checker.check_for_updates_version()

    if not newest_version:
        console.print(f"[green] 目前已是最新版本。當前版本：[cyan]{ProjectInfo.VERSION}[/cyan][/green]")
        return

    # 確認是否要更新
    if not yes:
        console.print(f"發現新版本：[cyan]{newest_version}[/cyan]")
        confirm = click.confirm("是否要更新？", default=True)

        if not confirm:
            console.print("[yellow] 已取消更新 [/yellow]")
            return

    # 更新
    console.print(f"[bold cyan] 正在更新至 {newest_version}...[/bold cyan]")

    try:
        runner = CommandRunner()

        cmd = ["pip", "install", ProjectInfo.GITHUB_REPO_URL, "-U"]
        runner.run_command(cmd)

        console.print("[green bold]✓ 更新成功 [/green bold]")
        console.print(
            f"[green] 已從 [cyan]{ProjectInfo.VERSION}[/cyan] 更新至 [cyan]{newest_version}[/cyan][/green]"
        )
    except Exception as e:
        console.print(f"[bold red]× 更新過程中發生錯誤：{str(e)}[/bold red]")


@click.group(invoke_without_command=True)
@click.option("--yes", "-y", is_flag=True, help="auto confirm")
@click.pass_context
def upgrade(ctx: click.Context, yes: bool = False) -> None:
    """更新 commit assistant 至最新版本"""
    # 如果沒有其他子命令，則執行更新
    if ctx.invoked_subcommand is None:
        _upgrade(yes)


@upgrade.command()
def check() -> None:
    """檢查更新"""
    checker = UpgradeChecker()

    newest_version = checker.check_for_updates_version()

    if newest_version:
        checker.print_update_message(newest_version)
    else:
        console.print(f"[green] 目前已是最新版本。當前版本：[cyan]{ProjectInfo.VERSION}[/cyan][/green]")
