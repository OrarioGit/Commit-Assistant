from datetime import datetime
from typing import Optional

import requests
from packaging import version

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.console_utils import console, loading_spinner


class UpgradeChecker:
    UNTAGGED_VERSION = "v0.0.0"
    CHECK_INTERVAL = 60 * 60 * 24  # 1天 每次檢查的時間間隔

    def get_latest_check_time(self) -> Optional[datetime]:
        """取得上次檢查更新的時間"""
        latest_check_file = ProjectPaths.RESOURCES_DIR / ProjectInfo.UPGRADE_CHECK_FILE

        if not latest_check_file.exists():
            return None

        try:
            with open(latest_check_file, "r", encoding="utf-8") as f:
                return datetime.fromisoformat(f.read())
        except Exception:
            return None

    def should_check_update(self) -> bool:
        """檢查是否要檢查更新"""
        last_check_time = self.get_latest_check_time()

        # 完全沒有檢查過，需要更新
        if last_check_time is None:
            return True

        # 距離上次檢查的時間超過 CHECK_INTERVAL，需要更新
        return (datetime.now() - last_check_time).total_seconds() > self.CHECK_INTERVAL

    def save_latest_check_time(self) -> None:
        """儲存最新的檢查時間"""
        latest_check_file = ProjectPaths.RESOURCES_DIR / ProjectInfo.UPGRADE_CHECK_FILE

        with open(latest_check_file, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())

    def check_for_updates_version(self) -> Optional[str]:
        """檢查是否有新版本

        Returns:
            Optional[str]: 如果有新版本，回傳新版本號；否則回傳 None
        """
        try:
            with loading_spinner("檢查更新中..."):
                # 獲取最新的版本號
                response = requests.get(ProjectInfo.RELEASE_TAG_URL)
                tags = [tag["name"] for tag in response.json()]

            # 按版本排序
            sorted_tags = sorted(tags, key=lambda x: version.parse(x.lstrip("v")), reverse=True)

            latest_tag = sorted_tags[0] if sorted_tags else self.UNTAGGED_VERSION
            current = version.parse(ProjectInfo.VERSION.lstrip("v"))

            # 如果有新版本，回傳新版本號
            if version.parse(latest_tag.lstrip("v")) > current:
                return latest_tag

            return None

        except Exception:
            console.print("[red]檢查更新失敗，請稍後再試")
            return None

    def print_update_message(self, newest_version: str) -> None:
        """印出更新訊息

        Args:
            newest_version (str): 最新版本號
        """
        console.print(
            f"[yellow]發現新版本 [cyan]{newest_version}[/cyan]！您可以透過以下方式更新：[/yellow]\n"
        )
        console.print("[yellow]1. 執行更新指令[/yellow]")
        console.print(f"   [green]{ProjectInfo.CLI_MAIN_COMMAND} upgrade[/green]")
        console.print("[yellow]2. 透過 pip 安裝最新版本[/yellow]")
        console.print(f"   [green]pip install {ProjectInfo.GITHUB_REPO_URL} -U[/green]\n")

    def run_version_check(self, force: bool = False) -> None:
        """執行版本檢查

        Args:
            force (bool, optional): 是否強制檢查更新. Defaults to False.
        """
        if not force and not self.should_check_update():
            return

        newest_version = self.check_for_updates_version()

        if newest_version:
            self.print_update_message(newest_version)

        self.save_latest_check_time()
