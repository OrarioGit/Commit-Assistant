import click

from commit_assistant.commands import commit, config, install, style, summary, update, upgrade
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.upgrade_checker import UpgradeChecker


@click.group()
@click.version_option(version=ProjectInfo.VERSION, prog_name=ProjectInfo.NAME)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Commit Assistant CLI 工具"""
    # 取得當前執行的命令
    cmd_name = ctx.invoked_subcommand

    # 當upgrade以外的命令執行時，檢查更新
    if cmd_name != "upgrade":
        upgrade_checker = UpgradeChecker()
        upgrade_checker.run_version_check()


# 註冊子命令
cli.add_command(commit)
cli.add_command(install)
cli.add_command(config)
cli.add_command(style)
cli.add_command(summary)
cli.add_command(update)
cli.add_command(upgrade)


if __name__ == "__main__":  # pragma: no cover
    cli()
