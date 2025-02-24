from typing import Generator
from unittest.mock import Mock, patch

import pytest
from google.generativeai.types import GenerateContentResponse

from commit_assistant.core.base_generator import BaseGeminiAIGenerator
from commit_assistant.utils.style_utils import CommitStyleManager


@pytest.fixture
def mock_genai() -> Generator[Mock, None, None]:
    """模擬 Google Generative AI"""
    with patch("commit_assistant.core.base_generator.genai") as mock:
        # 建立模擬的 GenerativeModel 實例
        model_instance = Mock()
        mock.GenerativeModel.return_value = model_instance

        # 設定實例的 generate_content 方法
        response = Mock(spec=GenerateContentResponse)
        model_instance.generate_content.return_value = response

        yield mock


def test_init_without_api_key() -> None:
    """測試使用者沒有設定 API key 的情況"""
    with patch.dict("os.environ", {}, clear=True):  # 清空環境變數
        with pytest.raises(ValueError, match="請先執行.*設定API金鑰"):
            BaseGeminiAIGenerator()


def test_init_with_api_key(mock_genai: Mock) -> None:
    """測試有 API key 的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "GENERATIVE_MODEL": "test-model"}):
        generator = BaseGeminiAIGenerator()

        # 驗證 API 設定
        mock_genai.configure.assert_called_once_with(api_key="test-key")
        mock_genai.GenerativeModel.assert_called_once_with("test-model")

        # 驗證物件建立
        assert generator.model == mock_genai.GenerativeModel.return_value
        assert isinstance(generator.style_manager, CommitStyleManager)


def test_init_with_default_model(mock_genai: Mock) -> None:
    """測試使用預設模型的情況"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        BaseGeminiAIGenerator()

        # 驗證使用預設模型
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash-exp")


def test_generate_content_success(mock_genai: Mock) -> None:
    """測試成功生成內容"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        # 創建一個新的 mock 作為 model
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # 設定預期的回應
        expected_response = Mock(spec=GenerateContentResponse)
        mock_model.generate_content.return_value = expected_response

        generator = BaseGeminiAIGenerator()

        # 執行生成
        response = generator._generate_content("test prompt")

        # 驗證結果
        assert response == expected_response
        mock_model.generate_content.assert_called_once_with("test prompt")


def test_generate_content_error(mock_genai: Mock, capsys: pytest.CaptureFixture) -> None:
    """測試生成內容失敗"""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        # 創建一個新的 mock 作為 model
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # 模擬生成錯誤
        mock_model.generate_content.side_effect = Exception("API Error")

        generator = BaseGeminiAIGenerator()

        # 執行生成
        response = generator._generate_content("test prompt")

        # 驗證結果
        assert response is None
        mock_model.generate_content.assert_called_once_with("test prompt")

        # 驗證錯誤訊息
        console_output = capsys.readouterr().out
        assert "生成內容時發生錯誤" in console_output
