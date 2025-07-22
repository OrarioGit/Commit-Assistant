from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, mock_open, patch

import pytest
from freezegun import freeze_time

from commit_assistant.core.paths import ProjectPaths
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.utils.upgrade_checker import UpgradeChecker


@pytest.fixture
def upgrade_checker() -> UpgradeChecker:
    """建立 UpgradeChecker 實例"""
    return UpgradeChecker()


@pytest.fixture
def upgrade_check_file(tmp_path: Path) -> Path:
    """建立測試用的檢查更新時間紀錄檔案"""
    file_path = ProjectPaths.RESOURCES_DIR / ProjectInfo.UPGRADE_CHECK_FILE
    file_path.touch()
    return file_path


def test_get_latest_check_time_file_not_exists(upgrade_checker: UpgradeChecker) -> None:
    """測試檢查更新時，上次檢測時間紀錄檔案不存在的情況"""
    with patch("pathlib.Path.exists", return_value=False):
        result = upgrade_checker.get_latest_check_time()
        assert result is None


def test_get_latest_check_time_valid_data(upgrade_checker: UpgradeChecker) -> None:
    """測試檢查更新時，上次檢測時間紀錄檔案存在且有有效資料的情況"""
    test_time = datetime.now()
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=test_time.isoformat())):
            result = upgrade_checker.get_latest_check_time()
            assert result == test_time


def test_get_latest_check_time_invalid_data(upgrade_checker: UpgradeChecker) -> None:
    """測試檢查更新時，上次檢測時間紀錄檔案存在但讀取資料錯誤的情況"""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="invalid_date")):
            result = upgrade_checker.get_latest_check_time()
            assert result is None


def test_should_check_update_no_previous_check(upgrade_checker: UpgradeChecker) -> None:
    """測試從未檢查過更新的情況"""
    with patch.object(UpgradeChecker, "get_latest_check_time", return_value=None):
        assert upgrade_checker.should_check_update() is True


def test_should_check_update_recent_check(upgrade_checker: UpgradeChecker) -> None:
    """測試最近檢查過更新的情況"""
    recent_time = datetime.now() - timedelta(seconds=UpgradeChecker.CHECK_INTERVAL - 100)
    with patch.object(UpgradeChecker, "get_latest_check_time", return_value=recent_time):
        # 上次檢測時間距離現在不到 CHECK_INTERVAL，不需要檢查
        assert upgrade_checker.should_check_update() is False


def test_should_check_update_old_check(upgrade_checker: UpgradeChecker) -> None:
    """測試很久以前檢查過更新的情況"""
    old_time = datetime.now() - timedelta(seconds=UpgradeChecker.CHECK_INTERVAL + 100)
    with patch.object(UpgradeChecker, "get_latest_check_time", return_value=old_time):
        # 超過 CHECK_INTERVAL，需要檢查
        assert upgrade_checker.should_check_update() is True


@freeze_time("2025-01-01 12:00:00")
def test_save_latest_check_time(upgrade_checker: UpgradeChecker, upgrade_check_file: Path) -> None:
    """測試保存最新的檢查時間"""
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        upgrade_checker.save_latest_check_time()

        mock_file.assert_called_once_with(upgrade_check_file, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with("2025-01-01T12:00:00")


@pytest.mark.parametrize(
    "current_version,latest_tag,expected_result",
    [
        ("v1.0.0", "v1.1.0", "v1.1.0"),  # 新版本檢查
        ("v1.1.0", "v1.0.0", None),  # 當前版本比最新版本新
        ("v1.0.0", "v1.0.0", None),  # 當前版本已經是最新了
    ],
)
def test_check_for_updates_version(
    current_version: str, latest_tag: str, expected_result: Optional[str], upgrade_checker: UpgradeChecker
) -> None:
    """測試檢查是否有新版本"""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"name": latest_tag}]

    # mock 發請請求的函數
    with patch("requests.get", return_value=mock_response):
        with patch.object(ProjectInfo, "VERSION", current_version):
            result = upgrade_checker.check_for_updates_version()
            assert result == expected_result


def test_check_for_updates_version_exception(upgrade_checker: UpgradeChecker) -> None:
    """測試檢查是否有新版本時發生錯誤"""
    with patch("requests.get", side_effect=Exception):
        result = upgrade_checker.check_for_updates_version()
        assert result is None


def test_print_update_message(upgrade_checker: UpgradeChecker, capsys: pytest.CaptureFixture) -> None:
    """測試印出更新提示訊息"""
    upgrade_checker.print_update_message("v2.0.0")

    captured = capsys.readouterr()
    assert "發現新版本 v2.0.0！您可以透過以下方式更新：" in captured.out
    assert "執行更新指令" in captured.out
    assert "commit-assistant upgrade" in captured.out
    assert "透過 pip 安裝最新版本" in captured.out


def test_run_version_check_no_update_needed(upgrade_checker: UpgradeChecker) -> None:
    """測試不需要檢查更新的情況"""
    with patch.object(UpgradeChecker, "should_check_update", return_value=False):
        with patch.object(UpgradeChecker, "check_for_updates_version") as mock_check:
            with patch.object(UpgradeChecker, "save_latest_check_time") as mock_save:
                upgrade_checker.run_version_check(force=False)
                mock_check.assert_not_called()
                mock_save.assert_not_called()


def test_run_version_check_force_update(upgrade_checker: UpgradeChecker) -> None:
    """測試強制檢查更新的情況"""
    with patch.object(UpgradeChecker, "should_check_update", return_value=False):
        with patch.object(UpgradeChecker, "check_for_updates_version", return_value=None) as mock_check:
            with patch.object(UpgradeChecker, "save_latest_check_time") as mock_save:
                upgrade_checker.run_version_check(force=True)
                mock_check.assert_called_once()
                mock_save.assert_called_once()


def test_run_version_check_new_version_available(upgrade_checker: UpgradeChecker) -> None:
    """測試有新版本可用的情況"""
    with patch.object(UpgradeChecker, "should_check_update", return_value=True):
        with patch.object(UpgradeChecker, "check_for_updates_version", return_value="v2.0.0"):
            with patch.object(UpgradeChecker, "print_update_message") as mock_print:
                with patch.object(UpgradeChecker, "save_latest_check_time") as mock_save:
                    upgrade_checker.run_version_check()
                    mock_print.assert_called_once_with("v2.0.0")
                    mock_save.assert_called_once()


def test_run_version_check_no_new_version(upgrade_checker: UpgradeChecker) -> None:
    """測試沒有新版本可用的情況"""
    with patch.object(UpgradeChecker, "should_check_update", return_value=True):
        with patch.object(UpgradeChecker, "check_for_updates_version", return_value=None):
            with patch.object(UpgradeChecker, "print_update_message") as mock_print:
                with patch.object(UpgradeChecker, "save_latest_check_time") as mock_save:
                    upgrade_checker.run_version_check()
                    mock_print.assert_not_called()
                    mock_save.assert_called_once()
