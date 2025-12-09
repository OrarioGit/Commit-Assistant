from typing import Generator
from unittest.mock import Mock, patch

import pytest
from google.genai.types import GenerateContentResponse

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.enums.config_key import ConfigKey
from commit_assistant.enums.default_value import DefaultValue
from commit_assistant.utils.style_utils import CommitStyleManager


@pytest.fixture
def mock_genai() -> Generator[Mock, None, None]:
    """模擬 Google Generative AI"""
    with patch("commit_assistant.core.base_generator.genai") as mock:
        # 建立模擬的 Client 實例
        client_instance = Mock()
        mock.Client.return_value = client_instance

        # 設定實例的 generate_content 方法
        response = Mock(spec=GenerateContentResponse)
        client_instance.models.generate_content.return_value = response

        yield mock


def test_init_without_api_key() -> None:
    """測試使用者沒有設定 API key 的情況"""
    with patch.dict("os.environ", {}, clear=True):  # 清空環境變數
        with pytest.raises(ValueError, match="請先執行.*設定 API 金鑰"):
            BaseGeminiAIGenerator()


def test_init_with_api_key(mock_genai: Mock) -> None:
    """測試有 API key 的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", ConfigKey.USE_MODEL.value: "test-model"}):
        generator = BaseGeminiAIGenerator()

        # 驗證 API 設定
        mock_genai.Client.assert_called_once_with(api_key="test-key")

        # 驗證物件建立
        assert generator.model == "test-model"
        assert isinstance(generator.style_manager, CommitStyleManager)


def test_init_with_default_model(mock_genai: Mock) -> None:
    """測試使用預設模型的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        generator = BaseGeminiAIGenerator()

        # 驗證使用預設模型
        assert generator.model == DefaultValue.DEFAULT_MODEL.value


def test_generate_content_success(mock_genai: Mock) -> None:
    """測試成功生成內容"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        # 創建一個新的 mock 作為 client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        # 設定預期的回應
        expected_response = Mock(spec=GenerateContentResponse)
        mock_client.models.generate_content.return_value = expected_response

        generator = BaseGeminiAIGenerator()

        # 執行生成
        response = generator._generate_content("test prompt")

        # 驗證結果
        assert response == expected_response
        mock_client.models.generate_content.assert_called_once_with(
            model=generator.model, contents="test prompt"
        )


def test_generate_content_error(mock_genai: Mock, capsys: pytest.CaptureFixture) -> None:
    """測試生成內容失敗"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        # 創建一個新的 mock 作為 client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client

        # 模擬生成錯誤
        mock_client.models.generate_content.side_effect = Exception("API Error")

        generator = BaseGeminiAIGenerator()

        # 執行生成
        response = generator._generate_content("test prompt")

        # 驗證結果
        assert response is None
        mock_client.models.generate_content.assert_called_once_with(
            model=generator.model, contents="test prompt"
        )

        # 驗證錯誤訊息
        console_output = capsys.readouterr().out
        assert "生成內容時發生錯誤" in console_output
