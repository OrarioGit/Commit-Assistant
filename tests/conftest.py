# 部分測試使用 patch("google.genai") 模擬 Gemini SDK，
# patch 要求目標模組已經被 import，否則單獨執行這些測試檔時會出現 AttributeError
import google.genai  # noqa: F401
