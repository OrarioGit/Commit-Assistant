from unittest.mock import Mock, patch

import pytest

from commit_assistant.utils.environment_utils import (
    AGENT_ENV_VARS,
    is_agent_environment,
    is_interactive_environment,
)


@pytest.mark.parametrize("env_var", AGENT_ENV_VARS)
def test_is_agent_environment(env_var: str) -> None:
    """測試偵測到 agent 環境變數"""
    with patch.dict("os.environ", {env_var: "1"}, clear=True):
        assert is_agent_environment() is True


def test_is_not_agent_environment() -> None:
    """測試沒有任何 agent 環境變數"""
    with patch.dict("os.environ", {}, clear=True):
        assert is_agent_environment() is False


def test_is_interactive_environment_in_agent() -> None:
    """測試 agent 環境即使有終端機也不進行互動"""
    with (
        patch.dict("os.environ", {"CLAUDECODE": "1"}, clear=True),
        patch("sys.stdin", Mock(isatty=Mock(return_value=True))),
    ):
        assert is_interactive_environment() is False


@pytest.mark.parametrize("isatty", [True, False])
def test_is_interactive_environment_by_tty(isatty: bool) -> None:
    """測試依據 stdin 是否為終端機判斷"""
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("sys.stdin", Mock(isatty=Mock(return_value=isatty))),
    ):
        assert is_interactive_environment() is isatty


@pytest.mark.parametrize("stdin", [None, Mock(isatty=Mock(side_effect=ValueError))])
def test_is_interactive_environment_without_stdin(stdin: object) -> None:
    """測試 stdin 不存在或已關閉"""
    with patch.dict("os.environ", {}, clear=True), patch("sys.stdin", stdin):
        assert is_interactive_environment() is False
