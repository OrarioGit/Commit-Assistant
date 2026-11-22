"""AI 產出的 commit 建議資料結構

AI 會以結構化格式（JSON）回傳以下三個部分：
- commit_message: 可直接寫入 git 的 commit message 本體
- notes: 補充說明（為什麼這樣寫、選用哪個 type 等）
- warnings: 提交前的注意事項（機密外洩、除錯碼、漏 stage 的檔案等）
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WarningLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CommitWarning:
    level: WarningLevel
    message: str


@dataclass
class CommitSuggestion:
    message: str
    notes: str = ""
    warnings: List[CommitWarning] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommitSuggestion":
        """從 AI 回傳的結構化資料建立 CommitSuggestion

        Args:
            data (Dict[str, Any]): 符合 COMMIT_SUGGESTION_SCHEMA 的資料

        Raises:
            ValueError: commit_message 不存在或為空

        Returns:
            CommitSuggestion: 解析後的建議
        """
        message = clean_commit_message(str(data.get("commit_message") or ""))
        if not message:
            raise ValueError("AI 回傳的資料中沒有 commit_message")

        warnings = []
        for item in data.get("warnings") or []:
            if not isinstance(item, dict) or not item.get("message"):
                continue

            try:
                level = WarningLevel(str(item.get("level", "")).lower())
            except ValueError:
                # 無法辨識的等級一律視為 low，避免因為格式小問題遺失提醒
                level = WarningLevel.LOW

            warnings.append(CommitWarning(level=level, message=str(item["message"]).strip()))

        # 依嚴重程度排序，讓最重要的提醒顯示在最上面
        level_order = list(WarningLevel)
        warnings.sort(key=lambda w: level_order.index(w.level))

        return cls(message=message, notes=str(data.get("notes") or "").strip(), warnings=warnings)

    @classmethod
    def from_text(cls, text: str) -> "CommitSuggestion":
        """從純文字建立 CommitSuggestion（結構化輸出失敗時的備援）

        Args:
            text (str): AI 回傳的純文字

        Returns:
            CommitSuggestion: 只有 message 的建議
        """
        return cls(message=clean_commit_message(text))


# 要求 AI 回傳的 JSON Schema，Claude CLI 與 Gemini 共用
COMMIT_SUGGESTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "commit_message": {
            "type": "string",
            "description": "可直接寫入 git 的 commit message 本體，不含 markdown code fence 與任何說明",
        },
        "notes": {
            "type": "string",
            "description": "補充說明，例如 type 與 scope 的選擇理由；沒有則為空字串",
        },
        "warnings": {
            "type": "array",
            "description": "提交前需要注意的事項；沒有則為空陣列",
            "items": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": [level.value for level in WarningLevel]},
                    "message": {"type": "string"},
                },
                "required": ["level", "message"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["commit_message", "notes", "warnings"],
    "additionalProperties": False,
}


COMMIT_SUGGESTION_SYSTEM_PROMPT = """你是 git commit message 產生器，只負責依照使用者提供的規範撰寫 commit message，並在提交前做快速檢查。

輸出規則：
1. commit_message 只放可以直接寫入 git 的 commit message 本體，不得包含 markdown code fence、前言、解釋或任何對話文字。
2. 想補充的說明（例如為什麼選這個 type 或 scope）放在 notes，使用繁體中文，簡短即可。
3. 檢查變更內容，把提交前值得注意的事項放在 warnings，每項標註等級：
   - high：疑似洩漏機密（API key、密碼、token）、明顯會造成錯誤的程式碼、合併衝突標記、
     staged 的程式碼直接 import 或引用了「未被追蹤的新檔案」（只提交這次 commit 會導致程式無法執行）
   - medium：殘留的除錯輸出、被註解掉的大段程式碼
   - low：TODO、FIXME 等可以之後處理的事項
4. 使用者經常把一批修改拆成多個 commit 分段提交，因此：
   - 不要因為「還有其他檔案沒有 stage」或「沒有附上測試」就發出提醒
   - 只有在 staged 的 diff 中明確引用到未被追蹤的檔案時，才提醒漏 stage
5. 沒有值得注意的事項時，warnings 回傳空陣列，不要為了填寫而硬湊。
"""


_CODE_FENCE_PATTERN = re.compile(r"^```[\w-]*\s*\n(.*?)\n?```$", re.DOTALL)


def clean_commit_message(text: str) -> str:
    """清除 commit message 頭尾的 markdown code fence 與空白

    Args:
        text (str): 原始文字

    Returns:
        str: 清理後的 commit message
    """
    text = text.strip()

    match = _CODE_FENCE_PATTERN.match(text)
    if match:
        text = match.group(1)

    return text.strip().strip("`").strip()


def parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """解析 AI 回傳的 JSON 字串，失敗時回傳 None

    Args:
        raw (str): JSON 字串，可能被 code fence 包住

    Returns:
        Optional[Dict[str, Any]]: 解析後的資料
    """
    try:
        data = json.loads(clean_commit_message(raw))
    except (json.JSONDecodeError, TypeError):
        return None

    return data if isinstance(data, dict) else None
