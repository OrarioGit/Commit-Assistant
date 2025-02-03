import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from commit_assistant.utils.console_utils import console


class HookManager:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.hooks_dir = repo_path / ".git" / "hooks"
        self.hook_path = self.hooks_dir / "prepare-commit-msg"

    def backup_existing_hook(self) -> Optional[Path]:
        """備份現有的 hook"""
        if self.hook_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.hook_path.with_suffix(f".backup_{timestamp}")
            shutil.copy2(self.hook_path, backup_path)
            return backup_path
        return None

    def detect_husky(self, repo_path: Path) -> bool:
        """檢查是否使用了 husky"""
        husky_dir = repo_path / ".husky"
        husky_config = repo_path / "package.json"

        if husky_dir.exists():
            return True

        if husky_config.exists():
            try:
                import json

                with open(husky_config) as f:
                    package_json = json.load(f)
                    return "husky" in package_json.get("devDependencies", {})
            except Exception:
                pass

        return False

    def install_hook_husky(self, repo_path: Path, hook_content: str) -> None:
        """安裝 hook 到 husky 配置中"""
        husky_dir = repo_path / ".husky"
        hook_file = husky_dir / "prepare-commit-msg"

        # 確保目錄存在
        husky_dir.mkdir(exist_ok=True)

        if hook_file.exists():
            # 檢查使否該hook已經包含我們的命令
            current_content = hook_file.read_text(encoding="utf-8")
            if "commit-assistant" in current_content:
                console.print(
                    "[yellow]commit-assistant 已經安裝於 .husky/prepare-commit-msg，不需重複安裝[/yellow]"
                )
                return

            # 添加到現有hook的末尾
            with hook_file.open("a", encoding="utf-8") as f:
                f.write(f"\n# 以下內容由 commit-assistant 提供\n{hook_content}\n")
        else:
            # 創建新的 hook 文件
            with hook_file.open("w", encoding="utf-8") as f:
                f.write(f"# 以下內容由 commit-assistant 提供\n{hook_content}\n")

        # 設置執行權限
        hook_file.chmod(0o755)

    def merge_hooks(self, new_hook_content: str) -> str:
        """合併新舊 hook 的內容"""
        if not self.hook_path.exists():
            # 加入 bin/sh 開頭
            additional_content = "#!/bin/sh\n"
            additional_content += "\n# 以下內容由 commit-assistant 提供\n"

            new_hook_content = additional_content + new_hook_content
            return new_hook_content

        current_content = self.hook_path.read_text()

        # 如果已經包含我們的命令，則不需要重複添加
        if "commit-assistant" in current_content:
            return current_content

        # 合併腳本
        merged_content = "#!/bin/sh\n\n"
        merged_content += "# Original hook content\n"
        merged_content += current_content.replace("#!/bin/sh\n", "")
        merged_content += "\n# 以下內容由 commit-assistant 提供\n"
        merged_content += new_hook_content

        return merged_content

    def install_hook(self, hook_content: str) -> None:
        """安裝或更新 hook"""
        # 檢查是否使用 husky
        if self.detect_husky(self.repo_path):
            console.print("[yellow]偵測到husky，嘗試安裝於husky的設定中...[/yellow]")
            self.install_hook_husky(self.repo_path, hook_content)
            return

        # 備份現有的 hook
        backup_path = self.backup_existing_hook()
        if backup_path:
            console.print(f"正在備份舊版hook於 {backup_path}...")

        # 合併並寫入新的 hook
        merged_content = self.merge_hooks(hook_content)
        self.hook_path.write_text(merged_content, encoding="utf-8")
        self.hook_path.chmod(0o755)
