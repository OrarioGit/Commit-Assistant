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

    with patch("commit_assistant.core.base_generator.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="feat: claude generated message\n")
        response = generator._generate_content("test prompt")

    assert response == "feat: claude generated message"
    mock_run.assert_called_once_with(
        "claude -p",
        input="test prompt",
        shell=True,
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
