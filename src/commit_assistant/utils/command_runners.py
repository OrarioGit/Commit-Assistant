import locale
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from commit_assistant.utils.console_utils import console


class CommandRunner:
    """通用的 command runner 基類"""

    def __init__(self) -> None:
        if sys.platform == "win32":
            self.system_encoding = "utf-8"
        else:
            self.system_encoding = locale.getpreferredencoding()

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None
    ) -> str:
        """執行命令並處理編碼

        Args:
            cmd (List[str]): 要執行的命令
            cwd (Optional[Path]): 工作目錄
            env (Optional[Dict[str, str]]): 環境變數

        Returns:
            str: 命令執行結果
        """
        try:
            my_env = os.environ.copy()
            if env:
                my_env.update(env)

            my_env["PYTHONIOENCODING"] = self.system_encoding
            my_env["LANG"] = f"zh_TW.{self.system_encoding}"

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=my_env,
                encoding=self.system_encoding,
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                console.print(f"[red] 命令執行失敗：{stderr}[/red]")
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

            return stdout
        except Exception as e:
            console.print(f"[red] 執行命令時出錯：{e}[/red]")
            raise


# 不放進 diff 內容的 lock 檔
LOCK_FILE_NAMES = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    "go.sum",
]


class GitCommandRunner(CommandRunner):
    def __init__(self, repo_path: str) -> None:
        super().__init__()

        self.repo_path = Path(repo_path).resolve()
        self.validate_repo()

    def validate_repo(self) -> None:
        """驗證是否為有效的 git 倉庫"""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"路徑 {self.repo_path} 不是有效的 git 倉庫（找不到.git 資料夾）")

        console.print(f"[green] 成功找到 git 倉庫：{self.repo_path}[/green]")

    def get_staged_files(self) -> List[str]:
        """獲取暫存的文件列表"""
        cmd = ["git", "diff", "--cached", "--name-only"]
        result = self.run_git_command(cmd)
        return result.splitlines()

    def get_staged_diff(self) -> str:
        """獲取暫存的 diff 內容

        lock 檔的 diff 動輒上千行，對撰寫 commit message 沒有幫助，只會拖慢速度並增加用量，
        因此從 diff 中排除。檔名仍會出現在 get_staged_files 的結果中，AI 依然知道它們有變更。
        """
        excludes = [f":(exclude,glob)**/{name}" for name in LOCK_FILE_NAMES]
        cmd = ["git", "diff", "--cached", "--", ".", *excludes]
        result = self.run_git_command(cmd)
        return result

    def get_untracked_files(self) -> List[str]:
        """獲取尚未被 git 追蹤的文件列表（已排除 .gitignore 中的檔案）"""
        cmd = ["git", "ls-files", "--others", "--exclude-standard"]
        result = self.run_git_command(cmd)
        return result.splitlines()

    def get_commits_in_date_range(self, start_dt: datetime, end_dt: datetime, author: Optional[str]) -> str:
        """獲取指定日期範圍內的 commit message

        Args:
            start_dt: 起始時間
            end_dt: 結束時間
            author: 作者名稱

        Returns:
            str: commits 的完整內容
        """
        start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

        cmd = ["git", "log", f"--since={start_str}", f"--until={end_str}"]

        if author is not None and author.strip():
            cmd.extend(["--author", author])

        return self.run_git_command(cmd)

    def run_git_command(self, cmd: List[str]) -> str:
        """執行 git 命令並處理編碼

        Args:
            cmd (List[str]): 要執行的 git 命令

        Returns:
            str: 命令執行結果
        """
        return self.run_command(cmd, cwd=self.repo_path)
