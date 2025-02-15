import enum
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.console_utils import console


class HookVersion(enum.Enum):
    NOT_INSTALLED = "none"
    OLD = "old"
    NEW = "new"


class HookManager:
    # 定義Marker用來標記哪一塊是我們的hook 內容
    COMMIT_ASSISTANT_MARKER_START = "### BEGIN: commit-assistant hook section (DO NOT REMOVE) ###"
    COMMIT_ASSISTANT_MARKER_END = "### END: commit-assistant hook section (DO NOT REMOVE) ###"

    # 舊版標記
    # TODO: 如果確定所有使用者都已經更新，可以刪除這個標記以及相關邏輯
    OLD_MARKER = "# 以下內容由 commit-assistant 提供"

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.hooks_dir = repo_path / ".git" / "hooks"
        self.hook_path = self.hooks_dir / ProjectInfo.HOOK_TEMPLATE_NAME

    def _backup_existing_hook(self) -> Optional[Path]:
        """備份現有的 hook"""
        if self.hook_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.hook_path.with_suffix(f".backup_{timestamp}")
            shutil.copy2(self.hook_path, backup_path)
            return backup_path
        return None

    def _detect_husky(self) -> bool:
        """檢查是否使用了 husky"""
        husky_dir = self.repo_path / ".husky"
        husky_config = self.repo_path / "package.json"

        if husky_dir.exists():
            return True

        if husky_config.exists():
            try:
                with open(husky_config) as f:
                    package_json = json.load(f)
                    return "husky" in package_json.get("devDependencies", {})
            except Exception:
                pass

        return False

    def _install_hook_husky(self, hook_content: str) -> None:
        """安裝 hook 到 husky 配置中"""
        husky_dir = self.repo_path / ".husky"
        hook_file = husky_dir / ProjectInfo.HOOK_TEMPLATE_NAME

        # 確保目錄存在
        husky_dir.mkdir(exist_ok=True)

        # 準備包含標記的 hook 內容
        full_hook_content = (
            f"{self.COMMIT_ASSISTANT_MARKER_START}\n{hook_content}\n{self.COMMIT_ASSISTANT_MARKER_END}"
        )

        if hook_file.exists():
            # 檢查是否該hook已經包含我們的命令
            current_content = hook_file.read_text(encoding="utf-8")
            if self.COMMIT_ASSISTANT_MARKER_START in current_content:
                console.print(
                    "[yellow]commit-assistant 已經安裝於 .husky/prepare-commit-msg，不需重複安裝[/yellow]"
                )
                return

            # 添加到現有hook的末尾
            with hook_file.open("a", encoding="utf-8") as f:
                f.write(f"\n{full_hook_content}\n")
        else:
            # 創建新的 hook 文件
            with hook_file.open("w", encoding="utf-8") as f:
                f.write(f"{full_hook_content}\n")

        # 設置執行權限
        hook_file.chmod(0o755)

    def _inject_hooks(self, hook_template_content: str) -> str:
        """往使用者的 hook 文件中注入 commit-assistant 的內容"""
        # 使用者沒有自定義 hook，直接使用我們的模板
        if not self.hook_path.exists():
            # 加入 bin/sh 開頭和標記
            content = "#!/bin/sh\n\n"
            content += f"{self.COMMIT_ASSISTANT_MARKER_START}\n"
            content += hook_template_content
            content += f"\n{self.COMMIT_ASSISTANT_MARKER_END}\n"
            return content

        current_content = self.hook_path.read_text(encoding="utf-8")

        # 如果已經包含我們的hook，則不需要重複添加
        if self.COMMIT_ASSISTANT_MARKER_START in current_content:
            return current_content

        # 注入
        merged_content = "#!/bin/sh\n\n"
        merged_content += "# Original hook content\n"
        merged_content += current_content.replace("#!/bin/sh\n", "")
        merged_content += f"\n{self.COMMIT_ASSISTANT_MARKER_START}\n"
        merged_content += hook_template_content
        merged_content += f"\n{self.COMMIT_ASSISTANT_MARKER_END}\n"

        return merged_content

    def _replace_commit_assistant_section(self, current_content: str, new_hook_content: str) -> str:
        """替換文件中的 commit-assistant 部分"""
        # 透過標記來定位 commit-assistant 部分
        start_pattern = re.escape(self.COMMIT_ASSISTANT_MARKER_START + "\n")
        end_pattern = re.escape("\n" + self.COMMIT_ASSISTANT_MARKER_END)

        # 本次更新的內容
        # !注意：這裡的 new_hook_content 已經包含了標記
        replacement = (
            f"{self.COMMIT_ASSISTANT_MARKER_START}\n{new_hook_content}\n{self.COMMIT_ASSISTANT_MARKER_END}"
        )

        # 檢查是否存在 commit-assistant 部分
        if self.COMMIT_ASSISTANT_MARKER_START not in current_content:
            # 如果不存在，添加到文件末尾
            if not current_content.endswith("\n"):
                current_content += "\n"
            return current_content + f"\n{replacement}\n"

        # 使用正則表達式替換整個部分（包含標記）
        pattern = f"{start_pattern}.*?{end_pattern}"
        updated_content = re.sub(pattern, replacement, current_content, flags=re.DOTALL)

        return updated_content

    def _detect_hook_version(self, content: str) -> HookVersion:
        """檢測 hook 的版本

        Returns:
            HookVersion 新版本、舊版本或未安裝
        """
        if self.COMMIT_ASSISTANT_MARKER_START in content:
            return HookVersion.NEW
        elif self.OLD_MARKER in content:
            return HookVersion.OLD
        return HookVersion.NOT_INSTALLED

    def _extract_old_hook_content(self, content: str) -> str:
        """從舊版本的 hook 中提取 commit-assistant 的內容"""
        # 找到 OLD_MARKER 的位置
        start_idx = content.find(self.OLD_MARKER)
        if start_idx == -1:
            return ""

        # 找到從 marker 開始後的第一個換行符
        start_idx = content.find("\n", start_idx) + 1
        if start_idx == 0:  # 沒有找到換行符
            return ""

        # 取得該位置到最後的所有內容，這裡假設從 marker 開始後的內容就是 commit-assistant 的部分
        old_content = content[start_idx:]

        # 移除開頭和結尾的空行
        return old_content.strip()

    def _migrate_to_new_format(self, content: str) -> str:
        """將舊版本的 hook 格式遷移到新版本"""
        # 取得舊的內容
        old_hook_content = self._extract_old_hook_content(content)

        # 找到 OLD_MARKER 的位置
        start_idx = content.find(self.OLD_MARKER)
        if start_idx == -1:
            return content

        # 保留 OLD_MARKER 之前的內容
        prefix = content[:start_idx].rstrip()

        # 創建新的 hook 內容
        new_section = f"\n\n{self.COMMIT_ASSISTANT_MARKER_START}\n{old_hook_content}\n{self.COMMIT_ASSISTANT_MARKER_END}\n"

        return prefix + new_section

    def _update_git_hook_with_version(self, new_hook_content: str) -> None:
        """更新 git hook，支援版本升級"""
        if not self.hook_path.exists():
            console.print("[yellow]未找到現有的 git hook，將進行全新安裝...[/yellow]")
            self.install_hook(new_hook_content)
            return

        # 讀取當前內容
        current_content = self.hook_path.read_text(encoding="utf-8")
        version = self._detect_hook_version(current_content)

        # 根據版本處理
        if version == HookVersion.OLD:
            console.print("[yellow]檢測到舊版本的 hook，正在升級...[/yellow]")
            # 先遷移到新格式
            current_content = self._migrate_to_new_format(current_content)

        # 使用新版本格式更新內容
        updated_content = self._replace_commit_assistant_section(current_content, new_hook_content)

        # 如果內容有變化才寫入
        if updated_content != current_content:
            # 備份當前版本
            backup_path = self._backup_existing_hook()
            if backup_path:
                console.print(f"[yellow]已備份當前 hook 至 {backup_path}[/yellow]")

            self.hook_path.write_text(updated_content, encoding="utf-8")
            self.hook_path.chmod(0o755)
            console.print("[green]已成功更新 git hook[/green]")
        else:
            console.print("[yellow]hook 內容已是最新版本[/yellow]")

    def _update_husky_hook_with_version(self, new_hook_content: str) -> None:
        """更新 husky hook，支援版本升級"""
        husky_dir = self.repo_path / ".husky"
        hook_file = husky_dir / ProjectInfo.HOOK_TEMPLATE_NAME

        if not hook_file.exists():
            console.print("[yellow]未找到現有的 husky hook，將進行全新安裝...[/yellow]")
            self._install_hook_husky(new_hook_content)
            return

        # 讀取當前內容
        current_content = hook_file.read_text(encoding="utf-8")
        version = self._detect_hook_version(current_content)

        # 根據版本處理
        if version == HookVersion.OLD:
            console.print("[yellow]檢測到舊版本的 husky hook，正在升級...[/yellow]")
            # 先遷移到新格式
            current_content = self._migrate_to_new_format(current_content)

        # 使用新版本格式更新內容
        updated_content = self._replace_commit_assistant_section(current_content, new_hook_content)

        # 如果內容有變化才寫入
        if updated_content != current_content:
            hook_file.write_text(updated_content, encoding="utf-8")
            hook_file.chmod(0o755)
            console.print("[green]已成功更新 husky hook[/green]")
        else:
            console.print("[yellow]husky hook 內容已是最新版本[/yellow]")

    def install_hook(self, hook_content: str) -> None:
        """安裝或更新 hook"""
        # 檢查是否使用 husky
        if self._detect_husky():
            console.print("[yellow]偵測到husky，嘗試安裝於husky的設定中...[/yellow]")
            self._install_hook_husky(hook_content)
            return

        # 備份現有的 hook
        backup_path = self._backup_existing_hook()
        if backup_path:
            console.print(f"已備份舊版hook於 {backup_path}...")

        # 將我們的 hook 內容注入到現有 hook 文件中
        injected_content = self._inject_hooks(hook_content)
        self.hook_path.write_text(injected_content, encoding="utf-8")
        self.hook_path.chmod(0o755)

    def update_hook(self, new_hook_content: str) -> None:
        """更新 hook 中的 commit-assistant 部分"""
        if self._detect_husky():
            self._update_husky_hook_with_version(new_hook_content)
        else:
            self._update_git_hook_with_version(new_hook_content)
