import shutil
from pathlib import Path

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.config_utils import _add_to_gitignore, console
from commit_assistant.utils.hook_manager import HookManager


class UpdateManager:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.hook_path = repo_path / ".git" / "hooks" / ProjectInfo.HOOK_TEMPLATE_NAME

        # 個人實際設定檔
        self.config_path = repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME

        # 範例設定檔
        self.example_config_path = (
            repo_path / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_EXAMPLE_NAME
        )

        self.hook_template_path = ProjectPaths.HOOKS_DIR / ProjectInfo.HOOK_TEMPLATE_NAME
        self.example_template_path = ProjectPaths.CONFIG_DIR / ProjectInfo.CONFIG_EXAMPLE_NAME
        self.installations_path = ProjectPaths.RESOURCES_DIR / ProjectInfo.INSTALLATIONS_FILE

    def _update_example_config(self) -> None:
        """更新 example 設定檔為最新模板內容"""
        console.print("[yellow] 開始更新設定檔範本...[/yellow]")

        if not self.example_config_path.parent.exists():
            console.print("[yellow] 發現設定檔資料夾不存在，正在建立...[/yellow]")
            self.example_config_path.parent.mkdir(parents=True)

        template_content = self.example_template_path.read_text(encoding="utf-8")
        self.example_config_path.write_text(template_content, encoding="utf-8")

        console.print("[green] 設定檔範本更新完成!![/green]\n")

    def _migrate_pre_example_config(self) -> None:
        """遷移 v0.1.12 以前的版本：.commit-assistant-config 不含 .example 對應檔"""
        if not self.config_path.exists() or self.example_config_path.exists():
            return

        console.print("[yellow] 偵測到舊版設定格式，正在遷移至新格式...[/yellow]")

        # 從模板建立 example 檔（不動使用者已有的個人設定）
        template_content = self.example_template_path.read_text(encoding="utf-8")
        self.example_config_path.write_text(template_content, encoding="utf-8")

        # 確保個人設定檔被 gitignore
        gitignore_entry = f"{ProjectInfo.REPO_ASSISTANT_DIR}/{ProjectInfo.CONFIG_TEMPLATE_NAME}"
        _add_to_gitignore(str(self.repo_path), gitignore_entry)

        console.print("[green] 遷移完成！[/green]")
        console.print(
            f"[yellow] 您的 {ProjectInfo.CONFIG_TEMPLATE_NAME} 已保留，並已自動加入 .gitignore。[/yellow]"
        )

    def update(self) -> None:
        """更新 hook 和 config 檔案"""
        # 處理更早期版本：config 在專案根目錄
        old_root_config_path = self.repo_path / ProjectInfo.CONFIG_TEMPLATE_NAME
        if old_root_config_path.exists():
            new_config_dir = self.repo_path / ProjectInfo.REPO_ASSISTANT_DIR
            new_config_dir.mkdir(exist_ok=True)

            console.print(f"[yellow] 偵測到舊版本的設定檔，正在移動到新位置 {new_config_dir}[/yellow]")
            shutil.move(old_root_config_path, self.config_path)
            console.print("[green] 設定檔移動完成!![/green]\n")

        # 處理 v0.1.12 版本遷移
        self._migrate_pre_example_config()

        # 更新 example config
        self._update_example_config()

        # 更新 hook
        hook_manager = HookManager(self.repo_path)
        new_hook_content = self.hook_template_path.read_text(encoding="utf-8")
        hook_manager.update_hook(new_hook_content)


if __name__ == "__main__":  # pragma: no cover
    UpdateManager(Path(".")).update()
