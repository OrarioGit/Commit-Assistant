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
    config_file = repo_root_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME

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


def _add_to_gitignore(repo_root: str, entry: str) -> None:
    """將指定路徑加入 .gitignore（若尚未存在）"""
    gitignore_path = Path(repo_root) / ".gitignore"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if entry in content:
            return
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write(f"\n# commit-assistant 個人設定（請勿提交）\n{entry}\n")
    else:
        gitignore_path.write_text(f"# commit-assistant 個人設定（請勿提交）\n{entry}\n", encoding="utf-8")


def install_config(repo_root: str) -> None:
    """
    安裝配置文件到專案根目錄

    - 建立 .commit-assistant-config.example 供團隊參考（提交至 repo）
    - 將 .commit-assistant-config 加入 .gitignore（個人設定，opt-in）
    """
    save_config_path = Path(repo_root) / ProjectInfo.REPO_ASSISTANT_DIR

    # 確保專案配置文件夾存在
    save_config_path.mkdir(exist_ok=True)

    example_file = save_config_path / ProjectInfo.CONFIG_EXAMPLE_NAME

    try:
        # 複製 example 模板到專案目錄
        default_example_file = ProjectPaths.CONFIG_DIR / ProjectInfo.CONFIG_EXAMPLE_NAME
        if not example_file.exists():
            shutil.copy(default_example_file, example_file)

        # 將個人設定檔加入 .gitignore
        gitignore_entry = f"{ProjectInfo.REPO_ASSISTANT_DIR}/{ProjectInfo.CONFIG_TEMPLATE_NAME}"
        _add_to_gitignore(repo_root, gitignore_entry)

        console.print(
            f"[green] 已建立 {ProjectInfo.CONFIG_EXAMPLE_NAME}，"
            f"請複製為 {ProjectInfo.CONFIG_TEMPLATE_NAME} 並填入您的設定後即可使用 [/green]"
        )
    except Exception as e:
        console.print(f"[red] 安裝配置文件失敗：{e}[/red]")
        return
