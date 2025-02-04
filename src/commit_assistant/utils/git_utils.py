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
        self.styles = {
            "conventional": {
                "prompt": """請根據以下的代碼變更生成符合 Conventional Commits 規範的 commit message。

                變更文件:
                {changed_files}
                變更內容:
                {diff_content}

                格式要求：
                <type>[optional scope]: <description>

                [optional body]

                [optional footer(s)]

                type 類型：
                - feat: 新功能
                - fix: Bug 修復
                - docs: 文件更新
                - style: 程式碼格式
                - refactor: 重構
                - perf: 效能優化
                - test: 測試
                - chore: 建置/工具

                要求：
                1. 必須使用繁體中文
                2. 簡潔但資訊完整
                3. 重大更新需包含 BREAKING CHANGE
                4. scope 需反映模組名稱""",
            },
            "emoji": {
                "prompt": """請根據以下的代碼變更生成使用 emoji 風格的 commit message。

                變更文件:
                {changed_files}
                變更內容:
                {diff_content}

                格式要求：
                <emoji> [模組名稱] 主要變更描述

                詳細說明：
                - 變更內容 1
                - 變更內容 2
                - 變更內容 3

                emoji 對照表：
                主要類型：
                - ✨ 新功能 (feat)
                - 🐛 Bug 修復 (fix)
                - ♻️ 重構 (refactor)
                - ⚡ 效能優化 (perf)
                - 📚 文件更新 (docs)

                次要類型：
                - 🎨 程式碼格式 (style)
                - 🧪 測試相關 (test)
                - 🔧 建置/工具 (chore)
                - 🔥 刪除代碼 (remove)
                - 🚀 部署相關 (deploy)
                - 🔒 安全性更新 (security)

                要求：
                1. 必須使用繁體中文
                2. emoji 和模組名稱皆為必要
                3. 主要描述精簡但明確
                4. 詳細說明條列重要變更
                5. 相關任務編號選填""",
            },
            "angular": {
                "prompt": """請根據以下的代碼變更生成符合 Angular Style 的 commit message。

                變更文件:
                {changed_files}
                變更內容:
                {diff_content}

                格式要求：
                <type>(<scope>): <subject>
                <BLANK LINE>
                <body>
                <BLANK LINE>
                <footer>

                規範：
                1. subject 不超過 50 字元
                2. body 每行不超過 72 字元
                3. type 必須是以下之一：
                - feat
                - fix
                - docs
                - style
                - refactor
                - perf
                - test
                - build
                - ci
                - chore
                - revert

                要求：
                1. 必須使用繁體中文
                2. scope 需反映模組名稱
                3. 詳細描述改動原因
                4. 標註重大更新""",
            },
            "custom": {
                "prompt": """請根據以下的代碼變更生成一個結構化的commit message。
                變更文件:
                {changed_files}
                變更內容:
                {diff_content}

                請使用以下格式生成新的commit message：
                [主要功能/模組名稱] (變更類型摘要)

                Bug修正:
                - [修復內容1]
                - [修復內容2]

                效能優化:
                - [優化內容1]
                - [優化內容2]

                新功能:
                - [功能內容1]
                - [功能內容2]

                要求：
                1. 必須使用繁體中文
                2. 分類要清晰（Bug修正、效能優化、新功能等）
                3. 分類下每個項目要簡潔但信息完整
                4. 如果某個分類沒有相關改動，則不需要包含該分類""",
            },
        }

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
