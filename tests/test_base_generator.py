import json
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.enums.default_value import DefaultValue
from commit_assistant.utils.style_utils import CommitStyleManager


@pytest.fixture
def mock_genai() -> Generator[Mock, None, None]:
    """模擬 Google Generative AI"""
    with patch("google.genai") as mock:
        client_instance = Mock()
        mock.Client.return_value = client_instance
        client_instance.models.generate_content.return_value = Mock(text="generated text")
        yield mock


def test_init_without_api_key() -> None:
    """測試使用者沒有設定 API key 的情況"""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="請先執行.*設定 API 金鑰"):
            BaseGeminiAIGenerator()


def test_init_with_api_key(mock_genai: Mock) -> None:
    """測試有 API key 的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", ConfigKey.USE_MODEL.value: "test-model"}):
        generator = BaseGeminiAIGenerator()

        mock_genai.Client.assert_called_once_with(api_key="test-key")
        assert generator.model == "test-model"
        assert isinstance(generator.style_manager, CommitStyleManager)


def test_init_with_default_model(mock_genai: Mock) -> None:
    """測試使用預設模型的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        generator = BaseGeminiAIGenerator()
        assert generator.model == DefaultValue.DEFAULT_MODEL.value


def test_init_with_claude_cli() -> None:
    """測試使用 Claude CLI 模式，不需要 Gemini API key"""
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        generator = BaseGeminiAIGenerator()

    assert generator._use_claude_cli is True
    assert isinstance(generator.style_manager, CommitStyleManager)


def test_generate_content_success(mock_genai: Mock) -> None:
    """測試成功生成內容（Gemini）"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.return_value = Mock(text="expected text")

        generator = BaseGeminiAIGenerator()
        response = generator._generate_content("test prompt")

        assert response == "expected text"
        mock_client.models.generate_content.assert_called_once_with(
            model=generator.model, contents="test prompt"
        )


def test_generate_content_error(mock_genai: Mock, capsys: pytest.CaptureFixture) -> None:
    """測試生成內容失敗（Gemini）"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API Error")

        generator = BaseGeminiAIGenerator()
        response = generator._generate_content("test prompt")

        assert response is None
        mock_client.models.generate_content.assert_called_once_with(
            model=generator.model, contents="test prompt"
        )
        console_output = capsys.readouterr().out
        assert "生成內容時發生錯誤" in console_output


def test_generate_content_with_claude_cli_success() -> None:
    """測試使用 Claude CLI 成功生成內容"""
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        generator = BaseGeminiAIGenerator()

    with (
        patch("commit_assistant.core.base_generator.shutil.which", return_value="/usr/bin/claude"),
        patch("commit_assistant.core.base_generator.subprocess.run") as mock_run,
    ):
        mock_run.return_value = Mock(returncode=0, stdout="feat: claude generated message\n")
        response = generator._generate_content("test prompt")

    assert response == "feat: claude generated message"
    mock_run.assert_called_once_with(
        [
            "/usr/bin/claude",
            "-p",
            "--model",
            "sonnet",
            "--effort",
            "low",
            "--tools",
            "",
            "--no-session-persistence",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--disable-slash-commands",
        ],
        input="test prompt",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_generate_content_with_claude_cli_error(capsys: pytest.CaptureFixture) -> None:
    """測試使用 Claude CLI 生成失敗（non-zero returncode）"""
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        generator = BaseGeminiAIGenerator()

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stderr="claude cli error", stdout="")
        response = generator._generate_content("test prompt")

    assert response is None
    console_output = capsys.readouterr().out
    assert "claude cli error" in console_output


def test_claude_cli_model_setting() -> None:
    """測試 Claude CLI 使用自訂模型，且不受 Gemini 的 USE_MODEL 影響"""
    env = {
        ConfigKey.USE_CLAUDE_CLI.value: "true",
        ConfigKey.CLAUDE_CLI_MODEL.value: "sonnet",
        ConfigKey.USE_MODEL.value: "gemini-model",
    }
    with patch.dict("os.environ", env, clear=True):
        generator = BaseGeminiAIGenerator()

    assert generator.model == "sonnet"
    assert generator.provider_label == "Claude CLI <sonnet>"


def test_claude_cli_default_model() -> None:
    """測試 Claude CLI 未設定模型時使用預設值"""
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        generator = BaseGeminiAIGenerator()

    assert generator.model == DefaultValue.DEFAULT_CLAUDE_CLI_MODEL.value


def test_gemini_provider_label(mock_genai: Mock) -> None:
    """測試 Gemini 的 provider 顯示名稱"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", ConfigKey.USE_MODEL.value: "test-model"}):
        generator = BaseGeminiAIGenerator()

    assert generator.provider_label == "Gemini <test-model>"


SCHEMA = {"type": "object"}
STRUCTURED = {"commit_message": "feat: message", "notes": "", "warnings": []}


def _claude_generator() -> BaseGeminiAIGenerator:
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        return BaseGeminiAIGenerator()


def test_generate_structured_with_claude_cli() -> None:
    """測試 Claude CLI 結構化輸出，system prompt 透過檔案傳遞"""
    generator = _claude_generator()
    captured = {}

    def fake_run(cmd: list, **kwargs: object) -> Mock:
        # 暫存檔在呼叫結束後就會刪除，因此在呼叫當下讀取內容
        prompt_file = cmd[cmd.index("--system-prompt-file") + 1]
        captured["system_prompt"] = Path(prompt_file).read_text(encoding="utf-8")
        captured["cmd"] = cmd
        return Mock(returncode=0, stdout=json.dumps({"structured_output": STRUCTURED, "result": ""}))

    with patch("commit_assistant.core.base_generator.subprocess.run", side_effect=fake_run):
        result = generator._generate_structured("prompt", "system\nprompt", SCHEMA)

    assert result == STRUCTURED
    assert captured["system_prompt"] == "system\nprompt"
    assert captured["cmd"][captured["cmd"].index("--output-format") + 1] == "json"
    assert json.loads(captured["cmd"][captured["cmd"].index("--json-schema") + 1]) == SCHEMA


def test_generate_structured_with_claude_cli_from_result_text() -> None:
    """測試 Claude CLI 沒有 structured_output 時，從 result 文字解析"""
    generator = _claude_generator()
    stdout = json.dumps({"result": "```json\n" + json.dumps(STRUCTURED) + "\n```"})

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout=stdout)
        assert generator._generate_structured("prompt", "system", SCHEMA) == STRUCTURED


def test_generate_structured_with_claude_cli_failed(capsys: pytest.CaptureFixture) -> None:
    """測試 Claude CLI 結構化輸出失敗"""
    generator = _claude_generator()

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="cli failed")
        assert generator._generate_structured("prompt", "system", SCHEMA) is None

    assert "cli failed" in capsys.readouterr().out


def test_generate_structured_with_claude_cli_invalid_json(capsys: pytest.CaptureFixture) -> None:
    """測試 Claude CLI 回傳無法解析的內容"""
    generator = _claude_generator()

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="not json")
        assert generator._generate_structured("prompt", "system", SCHEMA) is None

    assert "生成內容時發生錯誤" in capsys.readouterr().out


def test_generate_structured_with_gemini(mock_genai: Mock) -> None:
    """測試 Gemini 結構化輸出"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        generator = BaseGeminiAIGenerator()

    generator.client.models.generate_content.return_value = Mock(text=json.dumps(STRUCTURED))
    result = generator._generate_structured("prompt", "system", SCHEMA)

    assert result == STRUCTURED
    config = generator.client.models.generate_content.call_args.kwargs["config"]
    assert config.system_instruction == "system"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == SCHEMA


def test_generate_structured_with_gemini_empty_response(mock_genai: Mock) -> None:
    """測試 Gemini 回傳空內容"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        generator = BaseGeminiAIGenerator()

    generator.client.models.generate_content.return_value = Mock(text=None)
    assert generator._generate_structured("prompt", "system", SCHEMA) is None


def test_claude_cli_effort_setting() -> None:
    """測試 Claude CLI 使用自訂 effort"""
    env = {ConfigKey.USE_CLAUDE_CLI.value: "true", ConfigKey.CLAUDE_CLI_EFFORT.value: "high"}
    with patch.dict("os.environ", env, clear=True):
        generator = BaseGeminiAIGenerator()

    assert generator.effort == "high"

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="ok")
        generator._generate_content("prompt")

    cmd = mock_run.call_args.args[0]
    assert cmd[cmd.index("--effort") + 1] == "high"


def test_claude_cli_default_effort() -> None:
    """測試 Claude CLI 未設定 effort 時使用預設值"""
    with patch.dict("os.environ", {ConfigKey.USE_CLAUDE_CLI.value: "true"}, clear=True):
        generator = BaseGeminiAIGenerator()

    assert generator.effort == DefaultValue.DEFAULT_CLAUDE_CLI_EFFORT.value


def test_warn_deprecated_gemini_model(mock_genai: Mock, capsys: pytest.CaptureFixture) -> None:
    """測試使用已棄用的 Gemini 模型時顯示提醒"""
    env = {"GEMINI_API_KEY": "test-key", ConfigKey.USE_MODEL.value: "gemini-2.5-flash"}
    with patch.dict("os.environ", env):
        BaseGeminiAIGenerator()

    output = capsys.readouterr().out
    assert "gemini-2.5-flash 已被 Google 棄用" in output
    assert "gemini-3.5-flash-lite" in output


def test_no_warning_for_current_gemini_model(mock_genai: Mock, capsys: pytest.CaptureFixture) -> None:
    """測試使用目前的 Gemini 模型時不顯示提醒"""
    env = {"GEMINI_API_KEY": "test-key", ConfigKey.USE_MODEL.value: "gemini-3.5-flash-lite"}
    with patch.dict("os.environ", env):
        BaseGeminiAIGenerator()

    assert "棄用" not in capsys.readouterr().out
