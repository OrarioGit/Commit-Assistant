import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from commit_assistant.utils.command_runners import CommandRunner, GitCommandRunner


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


@patch("subprocess.Popen")
@patch("os.environ.copy")
def test_run_command_without_env(mock_environ_copy: MagicMock, mock_popen: MagicMock) -> None:
    """測試執行命令不帶額外環境變數"""
    # 設置模擬對象的返回值
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("command output", "")
    mock_popen.return_value = mock_process

    mock_env: dict[str, str] = {}
    mock_environ_copy.return_value = mock_env

    # 建立 CommandRunner 並執行命令
    runner = CommandRunner()
    with patch.object(runner, "system_encoding", "utf-8"):
        result = runner.run_command(["git", "status"])

    # 驗證環境變數有正確被設置
    assert mock_env["PYTHONIOENCODING"] == "utf-8"
    assert mock_env["LANG"] == "zh_TW.utf-8"

    # 驗證 subprocess.Popen 被正確調用
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == ["git", "status"]
    assert kwargs["env"] == mock_env
    assert kwargs["encoding"] == "utf-8"
    assert result == "command output"


@patch("subprocess.Popen")
@patch("os.environ.copy")
def test_run_command_with_env(mock_environ_copy: MagicMock, mock_popen: MagicMock) -> None:
    """測試執行命令帶額外環境變數"""
    # 設置模擬對象的返回值
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("command output", "")
    mock_popen.return_value = mock_process

    base_env = {"PATH": "/usr/bin", "HOME": "/home/user"}
    mock_environ_copy.return_value = base_env.copy()

    # 創建額外的環境變數
    custom_env = {"GIT_DIR": "/custom/git", "CUSTOM_VAR": "value"}

    # 創建 CommandRunner 實例並執行命令
    runner = CommandRunner()
    with patch.object(runner, "system_encoding", "utf-8"):
        result = runner.run_command(["git", "status"], env=custom_env, cwd=Path("/some/path"))

    # 預期被更新後的環境變數
    expected_env = {
        "PATH": "/usr/bin",
        "HOME": "/home/user",
        "GIT_DIR": "/custom/git",
        "CUSTOM_VAR": "value",
        "PYTHONIOENCODING": "utf-8",
        "LANG": "zh_TW.utf-8",
    }

    # 驗證 my_env.update(env) 是否正確執行
    for key, value in custom_env.items():
        assert key in mock_environ_copy.return_value
        assert mock_environ_copy.return_value[key] == value

    # 驗證 subprocess.Popen 被正確調用
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == ["git", "status"]
    assert kwargs["env"] == expected_env
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["cwd"] == Path("/some/path")
    assert result == "command output"


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
    with pytest.raises(ValueError, match="不是有效的 git 倉庫"):
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


def test_get_commits_in_date_range_without_author(git_runner: GitCommandRunner) -> None:
    """測試獲取指定日期範圍內的 commits，不指定作者"""
    start_dt = datetime(2024, 2, 1)
    end_dt = datetime(2024, 2, 15)
    author = None
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
        assert "--author" not in cmd


def test_get_commits_in_date_range_author_is_empty_str(git_runner: GitCommandRunner) -> None:
    """測試獲取指定日期範圍內的 commits，作者為空字串"""
    start_dt = datetime(2024, 2, 1)
    end_dt = datetime(2024, 2, 15)
    author = ""
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
        assert "--author" not in cmd


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
