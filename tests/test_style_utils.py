import os
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from commit_assistant.core.project_config import ProjectInfo
from commit_assistant.enums.commit_style import CommitStyle, StyleScope
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.utils.style_utils import CommitStyleManager, StyleImporter, StyleValidator


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """建立臨時的 Git 儲存庫"""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    return repo_path


@pytest.fixture
def temp_style_file(tmp_path: Path) -> Path:
    """建立臨時的風格檔案"""
    style_content = """
    prompt: |
        Changed files: {changed_files}
        Diff content: {diff_content}
    """
    style_file = tmp_path / "test_style.yaml"
    style_file.write_text(style_content, encoding="utf-8")
    return style_file


@pytest.fixture
def mock_style_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """模擬專案存放風格的目錄"""
    tmp_style_path = tmp_path / "styles"

    with patch("commit_assistant.core.paths.ProjectPaths.STYLE_DIR", tmp_style_path):
        yield tmp_style_path


# StyleValidator 測試
def test_validate_content_success() -> None:
    """測試正確的內容驗證"""
    content = {"prompt": "Changed files: {changed_files}\nDiff content: {diff_content}"}

    try:
        # 驗證應該成功通過
        StyleValidator.validate_content(content)
        assert True
    except ValueError as e:
        assert False, f"不應該拋出異常，但拋出了：{str(e)}"


def test_validate_content_missing_required_field() -> None:
    """測試缺少必填欄位的情況"""
    content = {
        "description": "Some description"  # 缺少 prompt 欄位
    }
    with pytest.raises(ValueError) as exc_info:
        StyleValidator.validate_content(content)
    assert "缺少必要欄位：prompt" in str(exc_info.value)


def test_validate_content_missing_variables() -> None:
    """測試 prompt 中缺少必要變數的情況"""
    # 缺少 diff_content 變數
    content = {"prompt": "Changed files: {changed_files}"}
    with pytest.raises(ValueError) as exc_info:
        StyleValidator.validate_content(content)
    assert "prompt 中缺少必要變數：diff_content" in str(exc_info.value)


# StyleImporter 測試
def test_init_style_importer(temp_style_file: Path, mock_style_dir: Path) -> None:
    """測試初始化 StyleImporter 看是否正確"""
    importer = StyleImporter(temp_style_file, "test_style", True)
    assert importer.is_global
    assert importer.style_name == "test_style"
    assert str(mock_style_dir / "global") in str(importer.target_dir)


def test_init_style_importer_case_2(temp_style_file: Path, mock_style_dir: Path) -> None:
    """測試初始化 StyleImporter 看是否正確"""
    importer = StyleImporter(temp_style_file, None, False)
    assert importer.is_global is False
    assert importer.style_name == temp_style_file.stem  # 如果沒傳入指定名稱，則使用檔案名稱
    assert str(Path(ProjectInfo.REPO_ASSISTANT_DIR) / "style") in str(importer.target_dir)


def test_import_invalid_repo(tmp_path: Path, temp_style_file: Path) -> None:
    """測試在無效的 Git repo 中匯入"""
    os.chdir(tmp_path)  # 切換到非 Git 儲存庫目錄

    with pytest.raises(ValueError) as exc_info:
        StyleImporter(temp_style_file, "test_style", False)
    assert "當前目錄不是有效的 git 倉庫" in str(exc_info.value)


def test_start_import_style(
    temp_style_file: Path, mock_style_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    """測試開始匯入風格"""
    importer = StyleImporter(temp_style_file, "test_style", True)
    importer.start_import()

    # 檢查檔案是否被複製
    assert (mock_style_dir / "global" / "test_style.yaml").exists()

    # 檢查提示訊息
    console_out = capsys.readouterr().out
    # 確認使用者有拿到正確的提示
    assert f"已匯入為 [{StyleScope.GLOBAL.value}] 模板" in console_out
    assert "風格名稱:test_style" in console_out


def test_start_import_and_has_duplicate_style(
    temp_style_file: Path,
    mock_style_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """測試開始匯入風格"""
    importer = StyleImporter(temp_style_file, "test_style", True)
    importer.start_import()

    # 檢查檔案是否被複製
    assert (mock_style_dir / "global" / "test_style.yaml").exists()

    # 檢查提示訊息
    console_out = capsys.readouterr().out
    # 確認使用者有拿到正確的提示
    assert f"已匯入為 [{StyleScope.GLOBAL.value}] 模板" in console_out
    assert "風格名稱:test_style" in console_out

    # 更改檔案內容
    replace_content = """
     prompt: |
        some new content
        Changed files: {changed_files}
        Diff content: {diff_content}
    """
    temp_style_file.write_text(replace_content)

    # 匯入重複的風格
    importer = StyleImporter(temp_style_file, "test_style", True)

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者選擇 Y
        mock_confirm.return_value.ask.return_value = True

        # 檢查是否有覆寫
        importer.start_import()
        assert (mock_style_dir / "global" / "test_style.yaml").exists()

        new_style_content = (mock_style_dir / "global" / "test_style.yaml").read_text(encoding="utf-8")
        assert "some new content" in new_style_content


def test_start_import_and_has_duplicate_style_cancel_case(
    temp_style_file: Path,
    mock_style_dir: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """測試開始匯入風格"""
    importer = StyleImporter(temp_style_file, "test_style", True)
    importer.start_import()

    # 檢查檔案是否被複製
    assert (mock_style_dir / "global" / "test_style.yaml").exists()

    # 檢查提示訊息
    console_out = capsys.readouterr().out
    # 確認使用者有拿到正確的提示
    assert f"已匯入為 [{StyleScope.GLOBAL.value}] 模板" in console_out
    assert "風格名稱:test_style" in console_out

    # 更改檔案內容
    replace_content = """
    prompt: |
        some new content
        Changed files: {changed_files}
        Diff content: {diff_content}
    """
    temp_style_file.write_text(replace_content)

    # 清除之前的輸出
    capsys.readouterr()

    # 匯入重複的風格
    new_importer = StyleImporter(temp_style_file, "test_style", True)

    # 確保 target_file 確實存在
    assert new_importer.target_file.exists(), "目標檔案應該存在才能測試取消覆寫的情況"

    with patch("questionary.confirm") as mock_confirm:
        # 模擬使用者選擇 N
        mock_confirm.return_value.ask.return_value = False

        importer.start_import()

        # 檢查提示訊息
        console_out = capsys.readouterr().out
        assert "已取消匯入" in console_out


# CommitStyleManager 測試
def test_get_style_path_project(temp_git_repo: Path) -> None:
    """測試獲取專案風格路徑"""
    manager = CommitStyleManager()

    # 將測試用的 style_dir 指定到 manager 底下做測試
    style_dir = temp_git_repo / ProjectInfo.REPO_ASSISTANT_DIR / "style"
    style_dir.mkdir(parents=True)
    manager.project_styles_dir = style_dir

    # 建立一個假的 yaml 風格檔
    style_file = style_dir / "test_style.yaml"
    style_file.write_text("prompt: test")

    path, is_global = manager.get_style_path("test_style")
    assert path == style_file
    assert not is_global


def test_get_style_path_global(temp_git_repo: Path) -> None:
    """測試獲取全域的風格路徑"""
    manager = CommitStyleManager()

    # 將測試用的 style_dir 指定到 manager 底下做測試
    style_dir = temp_git_repo / "global"
    style_dir.mkdir(parents=True)
    manager.global_styles_dir = style_dir

    # 建立一個假的 yaml 風格檔
    style_file = style_dir / "test_style.yaml"
    style_file.write_text("prompt: test")

    path, is_global = manager.get_style_path("test_style")
    assert path == style_file
    assert is_global


def test_get_style_path_system(temp_git_repo: Path) -> None:
    """測試獲取系統內建的風格路徑"""
    manager = CommitStyleManager()

    # 將測試用的 style_dir 指定到 manager 底下做測試
    style_dir = temp_git_repo / "system"
    style_dir.mkdir(parents=True)
    manager.system_styles_dir = style_dir

    # 建立一個假的 yaml 風格檔
    style_file = style_dir / "test_style.yaml"
    style_file.write_text("prompt: test")

    path, is_global = manager.get_style_path("test_style")
    assert path == style_file
    assert not is_global


def test_get_style_path_not_found() -> None:
    """測試獲取不存在的風格"""
    manager = CommitStyleManager()
    with pytest.raises(ValueError) as exc_info:
        manager.get_style_path("non_existent_style")
    assert "找不到風格模板" in str(exc_info.value)


def test_set_project_commit_style_style_not_found(tmp_path: Path) -> None:
    """測試設定不存在的風格"""
    manager = CommitStyleManager()

    # Mock get_style_path 拋出異常
    with patch.object(manager, "get_style_path", side_effect=ValueError("找不到風格")):
        with pytest.raises(ValueError) as exc_info:
            manager.set_project_commit_style("non_existent_style")
        assert "找不到已設定風格模板" in str(exc_info.value)


def test_set_project_commit_style_config_not_found(tmp_path: Path) -> None:
    """測試設定檔不存在的情況"""
    manager = CommitStyleManager()

    # Mock get_style_path 返回成功
    with patch.object(manager, "get_style_path", return_value=(Mock(), False)):
        with pytest.raises(ValueError) as exc_info:
            manager.set_project_commit_style("test_style")
        assert "找不到" in str(exc_info.value)
        assert ProjectInfo.CONFIG_TEMPLATE_NAME in str(exc_info.value)


def test_set_project_commit_style_update_existing(tmp_path: Path) -> None:
    """測試更新現有的 COMMIT_STYLE 設定"""
    # 準備測試環境
    manager = CommitStyleManager()
    config_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir(parents=True)
    config_file = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME

    # 建立初始設定檔
    initial_content = f"""# 這是註解
        {ConfigKey.COMMIT_STYLE.value}=old_style
        SOME_OTHER_KEY=value
    """
    config_file.write_text(initial_content, encoding="utf-8")

    # Mock 必要的屬性和方法
    manager.project_config_file = config_file

    # Mock get_style_path 返回成功
    with patch.object(manager, "get_style_path", return_value=(Mock(), False)):
        manager.set_project_commit_style("new_style_name")

    # 驗證結果
    new_content = config_file.read_text(encoding="utf-8")
    assert f"{ConfigKey.COMMIT_STYLE.value}=new_style_name" in new_content
    assert "# 這是註解" in new_content
    assert "SOME_OTHER_KEY=value" in new_content  # 其他的 key 值應該要被保留且不能被更改
    assert "old_style" not in new_content  # 覆蓋舊有的數值


def test_set_project_commit_style_add_new(tmp_path: Path) -> None:
    """測試新增 COMMIT_STYLE 設定"""
    # 準備測試環境
    manager = CommitStyleManager()
    config_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir(parents=True)
    config_file = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME

    # 建立初始設定檔（不包含 COMMIT_STYLE）
    initial_content = """# 這是註解
            SOME_OTHER_KEY=value
        """
    config_file.write_text(initial_content, encoding="utf-8")

    # Mock 必要的屬性和方法
    manager.project_config_file = config_file

    # Mock get_style_path 返回成功
    with patch.object(manager, "get_style_path", return_value=(Mock(), False)):
        manager.set_project_commit_style("new_style_name")

    # 驗證結果
    new_content = config_file.read_text(encoding="utf-8")
    assert f"{ConfigKey.COMMIT_STYLE.value}=new_style_name" in new_content
    assert "# 這是註解" in new_content
    assert "SOME_OTHER_KEY=value" in new_content


def test_set_project_commit_style_global_warning(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """測試使用全域風格時的警告提示"""
    # 準備測試環境
    manager = CommitStyleManager()
    config_dir = tmp_path / ProjectInfo.REPO_ASSISTANT_DIR
    config_dir.mkdir(parents=True)
    config_file = config_dir / ProjectInfo.CONFIG_TEMPLATE_NAME

    # 建立初始設定檔
    config_file.write_text("# Empty config", encoding="utf-8")

    # Mock 必要的屬性和方法
    manager.project_config_file = config_file

    # Mock get_style_path 返回使用全域風格
    with patch.object(manager, "get_style_path", return_value=(Mock(), True)):
        manager.set_project_commit_style("global_style")

    # 驗證警告訊息
    captured = capsys.readouterr()
    assert f"[{StyleScope.GLOBAL.value}] 風格模板" in captured.out
    assert "其他專案成員可能無法使用" in captured.out
    assert "commit-assistant style add" in captured.out
    assert f"[{StyleScope.PROJECT.value}]" in captured.out


def test_get_prompt_valid_style() -> None:
    """測試獲取有效的 commit 風格提示"""
    manager = CommitStyleManager()
    changed_files = ["file1.py", "file2.py"]
    diff_content = "test diff"

    # 測試所有支援的風格
    for style in CommitStyle:
        prompt = manager.get_prompt(style.value, changed_files, diff_content)
        assert prompt
        assert "{changed_files}" not in prompt  # 確認變數有被替換
        assert "{diff_content}" not in prompt
        assert "file1.py" in prompt
        assert "test diff" in prompt


def test_get_prompt_invalid_style() -> None:
    """測試獲取無效的 commit 風格提示"""
    manager = CommitStyleManager()
    with pytest.raises(ValueError, match="找不到風格模板："):
        manager.get_prompt("invalid_style", [], "")
