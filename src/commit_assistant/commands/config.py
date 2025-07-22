import os
import sys

import click

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.utils.config_utils import load_config
from commit_assistant.utils.console_utils import console


def _mask_api_key(api_key: str) -> str:
    """遮蔽部分 API Key"""
    return f"{api_key[:5]}{'*' * (len(api_key) - 10)}{api_key[-5:]}"


@click.group()
def config() -> None:
    """配置管理命令"""


@config.command()
@click.option("--key", prompt="請輸入您的 Google Gemini API Key", hide_input=True)
def setup(key: str) -> None:
    """設定 Google Gemini API Key"""
    try:
        # 寫入 key 到.env 文件
        env_file = ProjectPaths.PACKAGE_DIR / ".env"

        if not env_file.exists():
            env_file.touch()

        with open(env_file, "w") as f:
            f.write(f"GEMINI_API_KEY={key}\n")

        console.print("[green]✓[/green] API Key 已成功保存")
        console.print("\n您可以使用以下命令來確認設定：")
        console.print("commit-assistant config show")

    except Exception as e:
        console.print(f"[red] 錯誤：無法保存 API Key：{e}[/red]")
        sys.exit(1)


@config.command()
def show() -> None:
    """顯示當前配置"""
    load_config()

    for config_member in ConfigKey:
        if config_member.value == ConfigKey.GEMINI_API_KEY.value:
            # 對於敏感信息，只顯示部分內容
            api_key = os.getenv(ConfigKey.GEMINI_API_KEY.value)

            if api_key is None:
                console.print(f"{config_member.value}: [yellow] 未配置 [/yellow]")
            else:
                console.print(_mask_api_key(api_key))
        else:
            config_member_value = os.getenv(config_member.value)
            console.print(f"{config_member.value}: {config_member_value}")


@config.command()
def clear() -> None:
    """清除所有配置"""
    # 判斷.env 文件是否存在，存在則刪除
    env_file = ProjectPaths.PACKAGE_DIR / ".env"
    if env_file.exists():
        if click.confirm("確定要清除所有配置嗎？"):
            env_file.unlink()
            console.print("[green]✓[/green] 配置已清除")
        else:
            console.print("[yellow] 動作已取消 [/yellow]")
    else:
        console.print("[yellow] 沒有找到配置文件 [/yellow]")


@config.command()
def get_api_key() -> None:
    """獲取 API Key"""
    load_config()

    api_key = os.getenv(ConfigKey.GEMINI_API_KEY.value)

    if api_key is None:
        console.print("[yellow]API Key 未配置 [/yellow]")
        return

    # 返回部分 API Key
    mask_api_key = _mask_api_key(api_key)
    console.print(f"API Key: {mask_api_key}")
