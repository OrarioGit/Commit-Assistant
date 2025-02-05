import locale
import os
import subprocess
import sys
from pathlib import Path
from typing import List

from commit_assistant.utils.console_utils import console


class GitCommandRunner:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.validate_repo()

        if sys.platform == "win32":
            self.system_encoding = "utf-8"
        else:
            self.system_encoding = locale.getpreferredencoding()

    def validate_repo(self) -> None:
        """驗證是否為有效的git倉庫"""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"路徑 {self.repo_path} 不是有效的git倉庫（找不到.git資料夾）")

        console.print(f"[green]成功找到git倉庫：{self.repo_path}[/green]")

    def get_staged_files(self) -> List[str]:
        """獲取暫存的文件列表"""
        cmd = ["git", "diff", "--cached", "--name-only"]
        result = self.run_git_command(cmd)
        return result.splitlines()

    def get_staged_diff(self) -> str:
        """獲取暫存的diff內容"""
        cmd = ["git", "diff", "--cached"]
        result = self.run_git_command(cmd)
        return result

    def run_git_command(self, cmd: List[str]) -> str:
        """執行git命令並處理編碼

        Args:
            cmd (List[str]): 要執行的git命令

        Returns:
            str: 命令執行結果
        """
        try:
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = self.system_encoding
            my_env["LANG"] = f"zh_TW.{self.system_encoding}"

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.repo_path,
                env=my_env,
                encoding=self.system_encoding,
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                console.print(f"[red]Git命令執行失敗: {stderr}[/red]")
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

            return stdout
        except Exception as e:
            console.print(f"[red]執行git命令時出錯: {e}[/red]")
            raise


class CommitStyleManager:
    def __init__(self) -> None:
        # prompts 檔案路徑
        self.default_prompt_path = Path(__file__).parent.parent / "prompts/default"
        self.custom_prompt_path = Path(__file__).parent.parent / "prompts/custom"
        self.styles = {}
        self.load_styles()

    def load_styles(self) -> None:
        """
        載入支援的風格
        """
        for default_prompt_file in self.default_prompt_path.glob("*.txt"):
            style_name = default_prompt_file.stem
            with open(default_prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()
                self.styles[style_name] = {"prompt": prompt}
        
        # 從 custom 目錄載入自定義風格
        for custom_prompt_file in self.custom_prompt_path.glob("*.txt"):
            style_name = custom_prompt_file.stem
            with open(custom_prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()
                self.styles[style_name] = {"prompt": prompt}

    def get_prompt(self, style: str, changed_files: List[str], diff_content: str) -> str:
        """
        獲取指定風格的 prompt

        Args:
            style (str): 風格名稱
            changed_files (List[str]): 變更的文件列表
            diff_content (str): 變更的內容

        Returns:
            str: 生成的 prompt"""
        if style not in self.styles:
            raise ValueError(f"不支援的風格：{style}")

        return self.styles[style]["prompt"].format(changed_files=changed_files, diff_content=diff_content)
