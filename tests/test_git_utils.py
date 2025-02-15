import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from commit_assistant.utils.git_utils import CommitStyleManager, GitCommandRunner


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """建立測試用的 git 倉庫"""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def git_runner(git_repo: Path) -> GitCommandRunner:
    """建立測試用的 GitCommandRunner"""
    return GitCommandRunner(str(git_repo))


def test_init_encoding_windows(git_repo: Path) -> None:
    """測試 Windows 平台的編碼設定"""
    with patch("sys.platform", "win32"):
        runner = GitCommandRunner(str(git_repo))
        assert runner.system_encoding == "utf-8"


def test_init_encoding_linux(git_repo: Path) -> None:
    """測試 Linux 平台的編碼設定"""
    with patch("sys.platform", "linux"), patch("locale.getpreferredencoding", return_value="UTF-8"):
        runner = GitCommandRunner(str(git_repo))
        assert runner.system_encoding == "UTF-8"


def test_init_encoding_mac(git_repo: Path) -> None:
    """測試 MacOS 平台的編碼設定"""
    with patch("sys.platform", "darwin"), patch("locale.getpreferredencoding", return_value="UTF-8"):
        runner = GitCommandRunner(str(git_repo))
        assert runner.system_encoding == "UTF-8"


def test_validate_repo(git_repo: Path) -> None:
    """測試驗證 git 倉庫"""
    runner = GitCommandRunner(str(git_repo))
    assert runner.repo_path == git_repo.resolve()


def test_validate_repo_invalid(tmp_path: Path) -> None:
    """測試驗證無效的 git 倉庫"""
    with pytest.raises(ValueError, match="不是有效的git倉庫"):
        GitCommandRunner(str(tmp_path))


def test_get_staged_files(git_runner: GitCommandRunner) -> None:
    """測試獲取暫存的檔案列表"""
    mock_output = "file1.py\nfile2.py"

    with patch.object(git_runner, "run_git_command") as mock_run:
        mock_run.return_value = mock_output
        files = git_runner.get_staged_files()

        assert files == ["file1.py", "file2.py"]
        mock_run.assert_called_once_with(["git", "diff", "--cached", "--name-only"])


def test_get_staged_diff(git_runner: GitCommandRunner) -> None:
    """測試獲取暫存的 diff 內容"""
    mock_diff = "mock diff content"

    with patch.object(git_runner, "run_git_command") as mock_run:
        mock_run.return_value = mock_diff
        diff = git_runner.get_staged_diff()

        assert diff == mock_diff
        mock_run.assert_called_once_with(["git", "diff", "--cached"])


def test_get_commits_in_date_range(git_runner: GitCommandRunner) -> None:
    """測試獲取指定日期範圍內的 commits"""
    start_dt = datetime(2024, 2, 1)
    end_dt = datetime(2024, 2, 15)
    author = "test_author"
    mock_log = "commit log content"

    with patch.object(git_runner, "run_git_command") as mock_run:
        mock_run.return_value = mock_log
        log = git_runner.get_commits_in_date_range(start_dt, end_dt, author)

        assert log == mock_log
        mock_run.assert_called_once()
        # 驗證命令參數
        cmd = mock_run.call_args[0][0]
        assert "--since=2024-02-01 00:00:00" in cmd
        assert "--until=2024-02-15 00:00:00" in cmd
        assert "--author" in cmd
        assert "test_author" in cmd


def test_run_git_command_success(git_runner: GitCommandRunner) -> None:
    """測試成功執行 git 命令"""
    mock_process = Mock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("output", "")

    with patch("subprocess.Popen", return_value=mock_process):
        output = git_runner.run_git_command(["git", "status"])
        assert output == "output"


def test_run_git_command_error(git_runner: GitCommandRunner) -> None:
    """測試執行 git 命令失敗"""
    mock_process = Mock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = ("", "error message")

    with patch("subprocess.Popen", return_value=mock_process):
        with pytest.raises(subprocess.CalledProcessError):
            git_runner.run_git_command(["git", "invalid-command"])


# CommitStyleManager 測試
def test_get_prompt_valid_style() -> None:
    """測試獲取有效的 commit 風格提示"""
    manager = CommitStyleManager()
    changed_files = ["file1.py", "file2.py"]
    diff_content = "test diff"

    # 測試所有支援的風格
    for style in ["conventional", "emoji", "angular", "custom"]:
        prompt = manager.get_prompt(style, changed_files, diff_content)
        assert prompt
        assert "{changed_files}" not in prompt  # 確認變數有被替換
        assert "{diff_content}" not in prompt
        assert "file1.py" in prompt
        assert "test diff" in prompt


def test_get_prompt_invalid_style() -> None:
    """測試獲取無效的 commit 風格提示"""
    manager = CommitStyleManager()
    with pytest.raises(ValueError, match="不支援的風格"):
        manager.get_prompt("invalid_style", [], "")
