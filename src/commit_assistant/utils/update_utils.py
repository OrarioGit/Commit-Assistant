import shutil
from pathlib import Path
from typing import Dict

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.config_utils import console
from commit_assistant.utils.hook_manager import HookManager


class UpdateManager:
    def __init__(self, repo_path: Path) -> None:
        # 先整理出要更新專案底下的相關檔案路徑
        self.repo_path = repo_path
        self.hook_path = repo_path / ".git" / "hooks" / ProjectInfo.HOOK_TEMPLATE_NAME
        self.config_path = repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME

        # 取出我們要更新的內容 (模板、設定檔)
        self.hook_template_path = ProjectPaths.HOOKS_DIR / ProjectInfo.HOOK_TEMPLATE_NAME
        self.config_template_path = ProjectPaths.CONFIG_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME
        self.installations_path = ProjectPaths.RESOURCES_DIR / ProjectInfo.INSTALLATIONS_FILE

    def _update_config(self) -> None:
        """更新設定檔，保留使用者自定義的設定值並與新模板合併"""

        console.print("[yellow] 開始更新設定檔...[/yellow]")

        # 讀取當前設定
        current_config = self._read_current_config()

        # 讀取模板設定並合併
        new_config = self._read_template_config()
        merged_config = self._merge_configs(current_config, new_config)

        # 寫入新設定
        self._write_merged_config(merged_config)

        console.print("[green] 設定檔更新完成!![/green]\n")

    def _read_template_config(self) -> Dict[str, str]:
        """讀取專案內 config 模板內容"""
        content = self.config_template_path.read_text(encoding="utf-8")
        return self._parse_config_content(content)

    def _parse_config_content(self, content: str) -> Dict[str, str]:
        """解析 config 內容為 dictionary 格式"""
        config = {}
        for line in content.splitlines():
            # 去除 tab，避免使用者習慣性的使用 tab 排版
            line = line.replace("\t", " ")

            # 去除前後空白
            line = line.strip()

            # 跳過註解和空行
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
        return config

    def _merge_configs(self, current_config: Dict[str, str], new_config: Dict[str, str]) -> Dict[str, str]:
        """合併當前設定和新設定，並保留 user 自定義的值"""
        merged_config = new_config.copy()
        for key, value in current_config.items():
            if key in new_config:
                merged_config[key] = value
        return merged_config

    def _write_merged_config(self, merged_config: Dict[str, str]) -> None:
        """將合併後的設定寫入檔案"""
        template_content = self.config_template_path.read_text(encoding="utf-8")
        result_lines = []

        for line in template_content.splitlines():
            if line.startswith("#") or not line.strip():
                result_lines.append(line)
            else:
                key = line.split("=", 1)[0].strip()
                result_lines.append(f"{key}={merged_config[key]}")

        # 如果 config 資料夾缺失，則先建立
        if not self.config_path.parent.exists():
            console.print("[yellow] 發現設定檔資料夾不存在，正在建立...[/yellow]")
            self.config_path.parent.mkdir(parents=True)

        self.config_path.write_text("\n".join(result_lines), encoding="utf-8")

    def _read_current_config(self) -> Dict[str, str]:
        """讀取當前的 config 檔內容"""
        if not self.config_path.exists():
            return {}

        return self._parse_config_content(self.config_path.read_text(encoding="utf-8"))

    def update(self) -> None:
        """更新 hook 和 config 檔案"""
        # 判斷是否有舊版本的 config 檔案
        # 在過往版本中，config 檔案是放在專案根目錄下的
        # 如果有的話，我們要期先移動到新的位置，再進行後續更新處理
        old_version_config_path = self.repo_path / ProjectInfo.CONFIG_TEMPLATE_NAME
        if old_version_config_path.exists():
            # 建立新版位置的資料夾
            new_config_path = self.repo_path / ProjectInfo.REPO_ASSISTANT_DIR
            new_config_path.mkdir(exist_ok=True)

            console.print(
                f"[yellow] 偵測到舊版本的設定檔，正在移動到新位置{self.repo_path}/{new_config_path}[/yellow]"
            )

            # 移動舊的 config 檔案
            shutil.move(old_version_config_path, new_config_path / ProjectInfo.CONFIG_TEMPLATE_NAME)
            console.print("[green] 設定檔移動完成!![/green]\n")

        # 更新 config
        self._update_config()

        # 更新 hook
        hook_manager = HookManager(self.repo_path)
        new_hook_content = self.hook_template_path.read_text(encoding="utf-8")
        hook_manager.update_hook(new_hook_content)


if __name__ == "__main__":  # pragma: no cover
    UpdateManager(Path(".")).update()
