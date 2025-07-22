import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import tomli
import tomli_w

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.console_utils import console


class InstallationManager:
    def __init__(self) -> None:
        self.installations_path = ProjectPaths.RESOURCES_DIR / ProjectInfo.INSTALLATIONS_FILE

    def _normalize_path(self, path: Path) -> str:
        """規範化路徑，使得路徑一致"""
        return str(path.resolve()).replace("\\", "/")

    def _generate_installation_id(self, repo_path: Path) -> str:
        """生成安裝紀錄的 ID"""
        normalized_path = self._normalize_path(repo_path)
        return hashlib.md5(normalized_path.encode()).hexdigest()

    def _read_installations(self) -> dict:
        """讀取歷史安裝紀錄"""
        if not self.installations_path.exists():
            return {}

        try:
            return tomli.loads(self.installations_path.read_text(encoding="utf-8"))
        except Exception as e:
            console.print(f"[red] 讀取配置文件時發生錯誤：{e}[/red]")
            return {}

    def _save_installations(self, installation_info: dict) -> None:
        """儲存安裝紀錄"""
        try:
            self.installations_path.write_text(tomli_w.dumps(installation_info), encoding="utf-8")
        except Exception as e:
            console.print(f"[red] 儲存配置文件時發生錯誤：{e}[/red]")

    def add_installation(self, repo_path: Path) -> None:
        """記錄新的安裝訊息"""
        installation_info = self._read_installations()

        # 規範化路徑，讓路徑都使用正斜線，使得不同平台下路徑一致
        normalized_path = self._normalize_path(repo_path)

        # 產生安裝 ID
        installation_id = self._generate_installation_id(repo_path)

        # 準備新的安裝記錄
        installation = {
            "id": installation_id,
            "repo_path": normalized_path,
            "version": ProjectInfo.VERSION,
            "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 更新安裝紀錄
        if "installations" not in installation_info:
            installation_info["installations"] = {}

        installation_info["installations"][installation_id] = installation
        self._save_installations(installation_info)

        console.print(f"[green] 已記錄安裝信息：{normalized_path}[/green]")

    def get_installation(self, repo_path: Path) -> Dict:
        """獲取安裝記錄"""
        installations_info = self._read_installations()

        # 取得安裝 ID
        installation_id = self._generate_installation_id(repo_path)

        if "installations" in installations_info and installation_id in installations_info["installations"]:
            return installations_info["installations"][installation_id]
        else:
            return {}

    def get_all_installations(self) -> List[Dict]:
        """獲取所有安裝記錄"""
        installations_info = self._read_installations()
        installations = []

        for _, info in installations_info.get("installations", {}).items():
            repo_path = info["repo_path"]

            # 檢查路徑是否仍然存在
            if Path(repo_path).exists():
                installations.append(info)
            else:
                console.print(f"[yellow] 警告：倉庫路徑不存在，將跳過：{repo_path}[/yellow]")

        return installations

    def remove_installation(self, repo_path: Path) -> None:
        """移除安裝記錄"""
        installations_info = self._read_installations()
        normalized_path = self._normalize_path(repo_path)

        # 取得安裝 ID
        installation_id = self._generate_installation_id(repo_path)

        # 移除安裝記錄
        if "installations" in installations_info and installation_id in installations_info["installations"]:
            del installations_info["installations"][installation_id]
            self._save_installations(installations_info)
            console.print(f"[green] 已移除安裝信息：{normalized_path} ID:{installation_id} [/green]")
        else:
            console.print(f"[yellow] 未找到安裝信息：{normalized_path}[/yellow]")


if __name__ == "__main__":  # pragma: no cover
    installation_manager = InstallationManager()
    installation_manager.add_installation(Path("."))
