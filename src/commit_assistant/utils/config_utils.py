import os
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import CommitStyle
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.utils.console_utils import console


def _load_config_from_config_file(config: dict[str, Any], repo_root: str) -> None:
    """
    從專案配置文件載入配置

    Args:
        config (dict[str, Any]): 設定
        repo_root (str): 專案根目錄路徑
    """
    repo_root_path = Path(repo_root)
    config_file = repo_root_path / ProjectInfo.REPO_ASSISTANT_DIR / ".commit-assistant-config"

    if not config_file.exists():
        return

    with open(config_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # '#' 開頭的行為註解，忽略
            # 其餘的設定進行寫入
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()


def load_config(repo_root: str = ".") -> None:
    """
    載入配置文件

    優先順序:
    1. 專案配置文件 (.commit-assistant-config)
    2. 環境變數 (.env)
    3. 默認值

    Args:
        repo_root (str, optional): 專案根目錄路徑。Defaults to ".".
    """
    # 定義默認配置
    config: dict[str, Any] = {
        ConfigKey.ENABLE_COMMIT_ASSISTANT.value: True,
        ConfigKey.USE_MODEL.value: "gemini-2.5-flash",
        ConfigKey.GEMINI_API_KEY.value: None,
        ConfigKey.COMMIT_STYLE.value: CommitStyle.CONVENTIONAL.value,
    }

    # 從 .env 載入，覆蓋默認配置
    dotenv_path = ProjectPaths.PACKAGE_DIR / ".env"
    load_dotenv(dotenv_path)
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            config[key] = env_value

    # 從專案配置文件載入
    try:
        _load_config_from_config_file(config, repo_root)
    except Exception as e:
        console.print(f"[yellow] 載入 commit-assistant config 失敗：{e}[/yellow]")

    # 將 config 設定進環境變數
    for key, value in config.items():
        if value is not None:
            os.environ[key] = str(value)


def install_config(repo_root: str) -> None:
    """
    安裝配置文件到專案根目錄
    """
    save_config_path = Path(repo_root) / ProjectInfo.REPO_ASSISTANT_DIR

    # 確保專案配置文件夾存在
    save_config_path.mkdir(exist_ok=True)

    config_file = save_config_path / ProjectInfo.CONFIG_TEMPLATE_NAME

    if config_file.exists():
        return

    try:
        # 複製默認的配置文件到專案根目錄
        default_config_file = ProjectPaths.CONFIG_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME

        shutil.copy(default_config_file, config_file)
    except Exception as e:
        console.print(f"[red] 安裝配置文件失敗：{e}[/red]")
        return
