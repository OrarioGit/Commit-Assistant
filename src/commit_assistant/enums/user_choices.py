from enum import Enum


class UserChoices(Enum):
    USE_AI_MESSAGE = "✅ 使用 AI 生成的 message"  # 使用 AI message
    EDIT_AI_MESSAGE = "📝 編輯 AI 生成的 message"  # 編輯 AI message
    CANCEL_OPERATION = "❌ 取消這次 commit"  # 取消操作
