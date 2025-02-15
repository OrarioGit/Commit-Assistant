import click

from commit_assistant.commands import commit, config, install, summary, update


@click.group()
def cli() -> None:
    """Commit Assistant CLI 工具"""


# 註冊子命令
cli.add_command(commit)
cli.add_command(install)
cli.add_command(config)
cli.add_command(summary)
cli.add_command(update)


if __name__ == "__main__":  # pragma: no cover
    cli()
