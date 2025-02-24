import sys
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from commit_assistant.commands.style import _validate_yaml, add, list, remove, template, use
from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import StyleScope

# 取得最原始的style Module
# 而不是被Click 裝飾器包裹後的Module(會失去原本的屬性，導致無法mock)
style_module = sys.modules["commit_assistant.commands.style"]


@pytest.fixture
def mock_style_dirs(tmp_path: Path) -> dict[str, Path]:
    """建立測試用的風格目錄(系統內建/全域/專案內)"""
    # 建立測試用的目錄結構
    system_dir = tmp_path / "system"
    global_dir = tmp_path / "global"
    project_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR / "style"

    for dir_path in [system_dir, global_dir, project_dir]:
        dir_path.mkdir(parents=True)

    # 建立測試用的 yaml 檔案
    test_content = """
    prompt: "test prompt {changed_files} {diff_content}"
    description: "Test Style"
    """

    (system_dir / "system_style.yaml").write_text(test_content, encoding="utf-8")
    (global_dir / "global_style.yaml").write_text(test_content, encoding="utf-8")
    (project_dir / "project_style.yaml").write_text(test_content, encoding="utf-8")

    return {"system": system_dir, "global": global_dir, "project": project_dir}


def test_validate_yaml_valid() -> None:
    """測試有效的 yaml 檔案驗證"""
    result = _validate_yaml(None, None, "test.yaml")
    assert isinstance(result, Path)
    assert str(result) == "test.yaml"


def test_validate_yaml_invalid() -> None:
    """測試無效的 yaml 檔案驗證"""
    with pytest.raises(click.BadParameter):
        # 這裡傳入txt 應該要被過濾出來
        _validate_yaml(None, None, "test.txt")


def test_list_command(tmp_path: Path, mock_style_dirs: dict[str, Path]) -> None:
    """測試列出風格指令"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        # Mock 路徑
        mock_paths.STYLE_DIR = mock_style_dirs["system"].parent

        runner = CliRunner()
        result = runner.invoke(list, ["--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert StyleScope.SYSTEM.value in result.output
        assert StyleScope.GLOBAL.value in result.output
        assert StyleScope.PROJECT.value in result.output
        assert "Test Style" in result.output  # 這裡是驗證是否有正確套用到mock_style_dirs中設定的yaml內容


def test_list_command_but_no_style_path_not_exist(tmp_path: Path) -> None:
    """測試列出風格指令，但所有路徑都不存在"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        # Mock 路徑
        mock_paths.STYLE_DIR = Path("not_exist_path")

        runner = CliRunner()
        result = runner.invoke(list, ["--repo-path", str(tmp_path)])

        assert result.exit_code == 0
        assert "尚無可用的 style" in result.output


def test_list_command_but_no_style_file_not_exist(mock_style_dirs: dict[str, Path]) -> None:
    """測試列出風格指令，但所有資料夾下都沒有風格檔案"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        # Mock 路徑
        mock_paths.STYLE_DIR = mock_style_dirs["system"].parent

        # 這裡故意刪除所有風格檔案
        for style_dir in mock_style_dirs.values():
            for style_file in style_dir.iterdir():
                style_file.unlink()

        runner = CliRunner()
        result = runner.invoke(list)

        assert result.exit_code == 0
        assert "尚無可用的 style" in result.output


def test_list_command_error(mock_style_dirs: dict[str, Path]) -> None:
    """測試列出所有風格指令時出錯"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        # Mock 路徑
        mock_paths.STYLE_DIR = mock_style_dirs["system"].parent

        # 這裡模擬open的時候出錯
        with patch("builtins.open", side_effect=Exception):
            runner = CliRunner()
            result = runner.invoke(list)

            assert result.exit_code == 0
            assert "讀取失敗" in result.output


def test_template_command_success(tmp_path: Path) -> None:
    """測試匯出模板指令成功的情況"""
    template_content = "template content"
    template_file = tmp_path / ProjectInfo.STYLE_TEMPLATE_NAME
    template_file.write_text(template_content, encoding="utf-8")

    with patch.object(style_module, "ProjectPaths") as mock_paths:
        mock_paths.STYLE_DIR = tmp_path

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(template, ["--output", str(output_dir)])

        assert result.exit_code == 0
        assert "成功" in result.output
        assert (output_dir / ProjectInfo.STYLE_TEMPLATE_NAME).exists()
        assert (output_dir / ProjectInfo.STYLE_TEMPLATE_NAME).read_text() == template_content


def test_template_command_template_not_found(tmp_path: Path) -> None:
    """測試匯出模板指令失敗的情況"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        # 這裡故意不建立模板檔
        mock_paths.STYLE_DIR = tmp_path

        runner = CliRunner()
        result = runner.invoke(template)

        assert result.exit_code == 0
        assert "失敗" in result.output
        assert "找不到" in result.output


def test_add_command(tmp_path: Path) -> None:
    """測試新增風格指令"""
    # 建立測試用的 yaml 檔案
    test_style = tmp_path / "test_style.yaml"
    test_style.write_text("""
        prompt: "test {changed_files} {diff_content}"
        description: "Test Style"
        """)

    with patch.object(style_module, "StyleImporter") as mock_importer:
        runner = CliRunner()
        result = runner.invoke(add, [str(test_style)])

        assert result.exit_code == 0
        mock_importer.assert_called_once()
        mock_importer.return_value.start_import.assert_called_once()


def test_add_command_error(tmp_path: Path) -> None:
    """測試新增風格指令失敗"""
    # 建立測試用的 yaml 檔案
    test_style = tmp_path / "test_style.yaml"
    test_style.write_text("""
        prompt: "test {changed_files} {diff_content}"
        description: "Test Style"
        """)

    with patch.object(style_module, "StyleImporter") as mock_importer:
        mock_importer.side_effect = Exception("Test Error")

        runner = CliRunner()
        result = runner.invoke(add, [str(test_style)])

        assert result.exit_code == 0
        mock_importer.assert_called_once()
        mock_importer.return_value.start_import.assert_not_called()
        assert "錯誤" in result.output


def test_use_command() -> None:
    """測試使用風格指令"""
    with patch.object(style_module, "CommitStyleManager") as mock_style_manager:
        runner = CliRunner()
        result = runner.invoke(use, ["test_style"])

        assert result.exit_code == 0
        mock_style_manager.return_value.set_project_commit_style.assert_called_once_with("test_style")
        assert "成功設定當前專案使用" in result.output


def test_use_command_error() -> None:
    """測試使用風格指令出錯"""
    with patch.object(style_module, "CommitStyleManager") as mock_style_manager:
        mock_style_manager.return_value.set_project_commit_style.side_effect = ValueError("Test Error")

        runner = CliRunner()
        result = runner.invoke(use, ["test_style"])

        assert result.exit_code == 0
        mock_style_manager.return_value.set_project_commit_style.assert_called_once_with("test_style")
        assert "錯誤" in result.output


def test_remove_command(tmp_path: Path) -> None:
    """測試刪除風格指令"""
    # 建立測試用的風格檔案
    style_dir = tmp_path / "global"
    style_dir.mkdir(parents=True)
    style_file = style_dir / "test_style.yaml"
    style_file.touch()

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者確認刪除
        mock_confirm.return_value.ask.return_value = True

        with patch.object(style_module, "ProjectPaths") as mock_paths:
            mock_paths.STYLE_DIR = tmp_path

            runner = CliRunner()
            result = runner.invoke(remove, ["test_style", "--global"])

            assert result.exit_code == 0
            assert "成功刪除" in result.output
            assert not style_file.exists()


def test_remove_command_project(tmp_path: Path) -> None:
    """測試刪除風格指令(專案內)"""
    # 建立測試用的風格檔案
    style_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR / "style"
    style_dir.mkdir(parents=True)
    style_file = style_dir / "test_style.yaml"
    style_file.touch()

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者確認刪除
        mock_confirm.return_value.ask.return_value = True

        # 模擬Path(".").absolute()的結果
        with patch("pathlib.Path.absolute") as mock_absolute:
            mock_absolute.return_value = tmp_path

            runner = CliRunner()
            result = runner.invoke(remove, ["test_style"])

            assert result.exit_code == 0
            assert "成功刪除" in result.output
            assert not style_file.exists()


def test_remove_command_cancel(tmp_path: Path) -> None:
    """測試取消刪除風格的情況"""
    # 建立測試用的風格檔案
    style_dir = tmp_path / "global"
    style_dir.mkdir(parents=True)
    style_file = style_dir / "test_style.yaml"
    style_file.touch()

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者取消刪除
        mock_confirm.return_value.ask.return_value = False

        with patch.object(style_module, "ProjectPaths") as mock_paths:
            mock_paths.STYLE_DIR = tmp_path

            runner = CliRunner()
            result = runner.invoke(remove, ["test_style", "--global"])

            assert result.exit_code == 0
            assert "已取消刪除" in result.output
            assert style_file.exists()


def test_remove_command_not_found(tmp_path: Path) -> None:
    """測試刪除不存在風格的情況"""
    with patch.object(style_module, "ProjectPaths") as mock_paths:
        mock_paths.STYLE_DIR = tmp_path

        runner = CliRunner()
        result = runner.invoke(remove, ["non_existent_style", "--global"])

        assert result.exit_code == 0
        assert "錯誤" in result.output
        assert "找不到" in result.output
        assert "請確認風格名稱是否正確，或者指定的層級是否正確" in result.output


def test_remove_command_error(tmp_path: Path) -> None:
    """測試刪除指令失敗的情況"""
    # 建立測試用的風格檔案
    style_dir = tmp_path / "global"
    style_dir.mkdir(parents=True)
    style_file = style_dir / "test_style.yaml"
    style_file.touch()

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者確認時出現錯誤
        mock_confirm.return_value.ask.side_effect = Exception("Test Error")

        with patch.object(style_module, "ProjectPaths") as mock_paths:
            mock_paths.STYLE_DIR = tmp_path

            # 這裡需要發生錯誤
            runner = CliRunner()
            result = runner.invoke(remove, ["test_style", "--global"])

            assert result.exit_code == 0
            assert "錯誤" in result.output
            assert style_file.exists()  # 原始檔案不應該被刪除
