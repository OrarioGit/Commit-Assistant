import pytest

from commit_assistant.core.commit_suggestion import (
    COMMIT_SUGGESTION_SCHEMA,
    CommitSuggestion,
    CommitWarning,
    WarningLevel,
    clean_commit_message,
    parse_json_object,
)


def test_from_dict() -> None:
    """測試從結構化資料建立建議，warnings 依嚴重程度排序"""
    suggestion = CommitSuggestion.from_dict(
        {
            "commit_message": "```\nfeat: add login\n```",
            "notes": "  新增功能  ",
            "warnings": [
                {"level": "low", "message": "缺少測試"},
                {"level": "HIGH", "message": "疑似寫死 API key"},
                {"level": "medium", "message": "殘留 print"},
            ],
        }
    )

    assert suggestion.message == "feat: add login"
    assert suggestion.notes == "新增功能"
    assert [w.level for w in suggestion.warnings] == [
        WarningLevel.HIGH,
        WarningLevel.MEDIUM,
        WarningLevel.LOW,
    ]


def test_from_dict_ignores_invalid_warnings() -> None:
    """測試格式錯誤的 warning 被忽略，無法辨識的等級視為 low"""
    suggestion = CommitSuggestion.from_dict(
        {
            "commit_message": "fix: bug",
            "warnings": ["not a dict", {"level": "high"}, {"level": "critical", "message": "未知等級"}],
        }
    )

    assert suggestion.notes == ""
    assert suggestion.warnings == [CommitWarning(level=WarningLevel.LOW, message="未知等級")]


@pytest.mark.parametrize("data", [{}, {"commit_message": ""}, {"commit_message": "```\n```"}])
def test_from_dict_without_message(data: dict) -> None:
    """測試沒有 commit_message 時拋出錯誤"""
    with pytest.raises(ValueError, match="commit_message"):
        CommitSuggestion.from_dict(data)


def test_from_text() -> None:
    """測試從純文字建立建議"""
    assert CommitSuggestion.from_text("  `fix: bug`  ") == CommitSuggestion(message="fix: bug")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("feat: add", "feat: add"),
        ("```\nfeat: add\n\nbody\n```", "feat: add\n\nbody"),
        ("```text\nfeat: add\n```", "feat: add"),
        ("  ```feat: add```  ", "feat: add"),
    ],
)
def test_clean_commit_message(text: str, expected: str) -> None:
    """測試清除 code fence"""
    assert clean_commit_message(text) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ("[1, 2]", None),
        ("not json", None),
    ],
)
def test_parse_json_object(raw: str, expected: object) -> None:
    """測試解析 JSON 物件"""
    assert parse_json_object(raw) == expected


def test_schema_levels_match_enum() -> None:
    """測試 schema 中的等級與 WarningLevel 一致"""
    level_schema = COMMIT_SUGGESTION_SCHEMA["properties"]["warnings"]["items"]["properties"]["level"]
    assert level_schema["enum"] == [level.value for level in WarningLevel]
