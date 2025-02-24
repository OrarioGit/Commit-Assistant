import click

from commit_assistant.commands import commit, config, install, style, summary, update
from commit_assistant.core.project_config import ProjectInfo


@click.group()
@click.version_option(version=ProjectInfo.VERSION, prog_name=ProjectInfo.NAME)
def cli() -> None:
    """Commit Assistant CLI 工具"""


# 註冊子命令
cli.add_command(commit)
cli.add_command(install)
cli.add_command(config)
cli.add_command(style)
cli.add_command(summary)
cli.add_command(update)


if __name__ == "__main__":  # pragma: no cover
    cli()
