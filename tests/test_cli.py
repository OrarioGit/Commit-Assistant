from click.testing import CliRunner

from commit_assistant.cli import cli


def test_cli_help() -> None:
    """測試CLI help指令"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    # 檢查是否有成功執行
    assert result.exit_code == 0
    # 檢查是否有顯示help訊息
    assert "Commit Assistant CLI 工具" in result.output
    # 檢查是否有顯示我們所有的子命令
    assert "commit" in result.output
    assert "install" in result.output
    assert "config" in result.output
    assert "summary" in result.output
    assert "update" in result.output


def test_cli_without_command() -> None:
    """測試沒有指定子命令時的行為"""
    runner = CliRunner()
    result = runner.invoke(cli)

    # 應該顯示幫助訊息而不是錯誤
    assert result.exit_code == 0
    assert "Commit Assistant CLI 工具" in result.output
