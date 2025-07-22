from pathlib import Path
from typing import List, Optional

import questionary
import yaml

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import StyleScope
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.utils.console_utils import console


class StyleValidator:
    """用於驗證 Style 內容的驗證器"""

    # 定義出 style yaml 必填欄位
    REQUIRED_FIELDS = ["prompt"]

    # 在內容中有那些變數需要被替換
    REQUIRED_VARIABLES = ["changed_files", "diff_content"]

    @classmethod
    def validate_content(cls, content: dict) -> None:
        """驗證內容是否正確

        Args:
            content (dict): 要驗證的內容

        Raises:
            ValueError: 當驗證失敗時拋出錯誤
        """
        # 1. 不可以缺少必填欄位
        missing_fields = [field for field in cls.REQUIRED_FIELDS if field not in content]
        if missing_fields:
            raise ValueError(
                f"缺少必要欄位：{', '.join(missing_fields)}，請檢查風格檔.yaml 中是否包含這些欄位"
            )

        # 2. prompt 中的替換變數必須存在
        for var in cls.REQUIRED_VARIABLES:
            if var not in content["prompt"]:
                raise ValueError(
                    f"prompt 中缺少必要變數：{var}，請檢查風格檔.yaml 的 prompt 中是否有包含這些變數"
                )


class StyleImporter:
    """用於管理 Style 的匯入"""

    def __init__(self, file_path: Path, style_name: Optional[str], is_global: bool) -> None:
        self.source_path = file_path.absolute()
        # 如果使用者有指定風格名稱，則使用指定名稱，否則使用檔案名稱
        self.style_name = style_name or self.source_path.stem
        self.is_global = is_global
        self.target_dir = self._get_target_directory()
        self.target_file = self.target_dir / f"{self.style_name}.yaml"

    def _get_target_directory(self) -> Path:
        """取得要匯入的 yaml 目標路徑"""
        # 全域，直接放在本套件目錄下
        if self.is_global:
            return ProjectPaths.STYLE_DIR / "global"

        # 專案，放在對應專案的 style 目錄下
        current_dir = Path(".").absolute()
        if not self._validate_repo(current_dir):
            raise ValueError("當前目錄不是有效的 git 倉庫")
        return current_dir / ProjectInfo.REPO_ASSISTANT_DIR / "style"

    def _validate_repo(self, current_dir: Path) -> bool:
        """驗證是否為有效的 git 倉庫"""
        git_dir = current_dir / ".git"
        return git_dir.exists()

    def _handle_existing_file(self) -> bool:
        """處理已存在的檔案"""
        if self.target_file.exists():
            return questionary.confirm(f"風格:{self.style_name} 已存在，是否要覆寫？").ask()
        return True

    def start_import(self) -> None:
        """開始匯入"""
        # 讀取和驗證匯入的內容是否正確
        with open(self.source_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        StyleValidator.validate_content(content)

        # 確保目標目錄存在並處理檔案
        self.target_dir.mkdir(parents=True, exist_ok=True)

        if not self._handle_existing_file():
            # 如果使用者選擇不複寫，則取消匯入
            console.print("[yellow] 已取消匯入 [/yellow]")
            return

        # 開始匯入
        with open(self.target_file, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True)

        # 匯入完成提示使用者訊息
        scope = f"[{StyleScope.GLOBAL.value}]" if self.is_global else f"[{StyleScope.PROJECT.value}]"
        console.print(f"[green]✓ 已匯入為{scope}模板 風格名稱:{self.style_name}[/green]")
        console.print("\n提示：可使用以下指令開始使用此風格應用到當前專案中")
        console.print(f"  commit-assistant style use {self.style_name}")


class CommitStyleManager:
    def __init__(self) -> None:
        # 各個風格的存放位置
        self.system_styles_dir = ProjectPaths.STYLE_DIR / "system"
        self.global_styles_dir = ProjectPaths.STYLE_DIR / "global"
        self.project_styles_dir = Path(".").absolute() / ProjectInfo.REPO_ASSISTANT_DIR / "style"

        # 專案設定檔的位置
        self.project_config_file = (
            Path(".").absolute() / ProjectInfo.REPO_ASSISTANT_DIR / ProjectInfo.CONFIG_TEMPLATE_NAME
        )

    def get_style_path(self, style_name: str) -> tuple[Path, bool]:
        """取得指定 style 的檔案路徑，如有重名優先使用專案模板

        Args:
            style_name (str): 風格名稱

        Returns:
            tuple[Path, bool]: 風格檔案路徑 (包含 yaml 檔案), 是否使用全域風格

        Raises:
            ValueError: 當找不到指定風格時拋出錯誤
        """
        is_global_style = False

        # 先檢查專案模板
        project_path = self.project_styles_dir / f"{style_name}.yaml"
        if project_path.exists():
            return (project_path, is_global_style)

        # 再檢查全域模板
        global_path = self.global_styles_dir / f"{style_name}.yaml"
        if global_path.exists():
            is_global_style = True  # 標記是使用全域模板
            return (global_path, is_global_style)

        # 最後檢查系統模板
        system_path = self.system_styles_dir / f"{style_name}.yaml"
        if system_path.exists():
            return system_path, is_global_style

        raise ValueError(f"找不到風格模板：{style_name}")

    def set_project_commit_style(self, style_name: str) -> None:
        """設定專案要使用的 commit style"""
        # 檢查指定的 style 是否存在
        try:
            _, use_global_style = self.get_style_path(style_name)
        except ValueError:
            raise ValueError(f"找不到已設定風格模板：{style_name}")

        # 更新設定檔
        if not self.project_config_file.exists():
            raise ValueError(
                f"找不到 [cyan]{ProjectInfo.CONFIG_TEMPLATE_NAME}[/cyan] 設定檔，請先執行 [cyan]commit-assistant install[/cyan] 或 [cyan]commit-assistant update[/cyan]"
            )

        # 讀取現有設定
        project_config_content = self.project_config_file.read_text(encoding="utf-8")

        # 更新 COMMIT_STYLE
        found = False
        result_lines = []
        for line in project_config_content.splitlines():
            if line.startswith("#") or not line.strip():
                result_lines.append(line)
            else:
                key = line.split("=", 1)[0].strip()

                # 如果找到 COMMIT_STYLE，則更新
                if key == ConfigKey.COMMIT_STYLE.value:
                    result_lines.append(f"{key}={style_name}")
                    found = True
                else:
                    result_lines.append(line)

        if not found:
            result_lines.append(f"{ConfigKey.COMMIT_STYLE.value}={style_name}")

        # 回寫專案設定檔
        self.project_config_file.write_text("\n".join(result_lines), encoding="utf-8")

        # 如果使用全域模板，有可能其他專案成員會無法使用
        # 這裡提示使用者注意
        if use_global_style:
            console.print(
                f"[yellow] 注意：當前使用本機的 [{StyleScope.GLOBAL.value}] 風格模板，其他專案成員可能無法使用 [/yellow]"
            )
            console.print(
                f"建議使用 [cyan]commit-assistant style add {style_name}[/cyan]，將其加入到 [{StyleScope.PROJECT.value}] 中\n"
            )

    def get_prompt(self, style: str, changed_files: List[str], diff_content: str) -> str:
        """
        獲取指定風格的 prompt

        Args:
            style (str): 風格名稱
            changed_files (List[str]): 變更的文件列表
            diff_content (str): 變更的內容

        Returns:
            str: 生成的 prompt
        """
        # 先取出要使用的風格檔案路徑
        style_path, _ = self.get_style_path(style)

        # 讀取 yaml prompt 內容
        with open(style_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # 檢查內容是否正確
        StyleValidator.validate_content(content)

        # 返回生成的 prompt
        return content["prompt"].format(changed_files=changed_files, diff_content=diff_content)
