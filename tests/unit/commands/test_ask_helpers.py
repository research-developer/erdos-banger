"""Unit tests for erdos ask command helpers (DEBT-017-D2)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING
from unittest import mock


if TYPE_CHECKING:
    import pytest

from erdos.commands.ask import (
    AskOptions,
    _execute_ask_query,
    _read_question_from_stdin,
    _show_progress_message,
    _validate_question_input,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput


class TestReadQuestionFromStdin:
    """Tests for _read_question_from_stdin() helper."""

    def test_read_single_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should read single line from stdin."""
        monkeypatch.setattr("sys.stdin", io.StringIO("What is the status?"))
        result = _read_question_from_stdin()
        assert result == "What is the status?"

    def test_read_multiline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should read multiple lines from stdin."""
        monkeypatch.setattr("sys.stdin", io.StringIO("Line 1\nLine 2\nLine 3"))
        result = _read_question_from_stdin()
        assert result == "Line 1\nLine 2\nLine 3"

    def test_trim_single_trailing_newline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should trim exactly one trailing newline."""
        monkeypatch.setattr("sys.stdin", io.StringIO("Question?\n"))
        result = _read_question_from_stdin()
        assert result == "Question?"

    def test_preserve_internal_newlines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should preserve internal newlines but trim trailing."""
        monkeypatch.setattr("sys.stdin", io.StringIO("Line 1\nLine 2\n"))
        result = _read_question_from_stdin()
        assert result == "Line 1\nLine 2"

    def test_empty_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle empty stdin."""
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        result = _read_question_from_stdin()
        assert result == ""

    def test_only_newline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle stdin with only newline."""
        monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
        result = _read_question_from_stdin()
        assert result == ""


class TestValidateQuestionInput:
    """Tests for _validate_question_input() helper."""

    def test_valid_question(self) -> None:
        """Should return None for valid question."""
        result = _validate_question_input("What is the status?")
        assert result is None

    def test_empty_string(self) -> None:
        """Should return error for empty string."""
        result = _validate_question_input("")
        assert result is not None
        assert isinstance(result, CLIOutput)
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "UsageError"
        assert "cannot be empty" in result.error["message"].lower()
        assert result.error["code"] == ExitCode.USAGE_ERROR

    def test_whitespace_only(self) -> None:
        """Should return error for whitespace-only string."""
        result = _validate_question_input("   \n\t  ")
        assert result is not None
        assert isinstance(result, CLIOutput)
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "UsageError"
        assert "cannot be empty" in result.error["message"].lower()
        assert result.error["code"] == ExitCode.USAGE_ERROR

    def test_question_with_leading_trailing_whitespace(self) -> None:
        """Should accept question with leading/trailing whitespace."""
        result = _validate_question_input("  What is this?  ")
        assert result is None


class TestShowProgressMessage:
    """Tests for _show_progress_message() helper."""

    def test_shows_message_in_human_mode(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should print progress message when json_output is False."""
        _show_progress_message(problem_id=6, json_output=False)
        captured = capsys.readouterr()
        assert "Problem 6" in captured.err
        assert "Retrieving" in captured.err

    def test_silent_in_json_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should not print anything when json_output is True."""
        _show_progress_message(problem_id=6, json_output=True)
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out == ""

    def test_problem_id_formatting(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should format problem ID correctly."""
        _show_progress_message(problem_id=123, json_output=False)
        captured = capsys.readouterr()
        assert "123" in captured.err


class TestExecuteAskQuery:
    """Tests for _execute_ask_query() helper."""

    @mock.patch("erdos.commands.ask.ask_question")
    def test_calls_ask_question_with_options(self, mock_ask: mock.Mock) -> None:
        """Should call ask_question with correct parameters."""
        mock_result = CLIOutput.ok("erdos ask", {"answer": "test"})
        mock_ask.return_value = mock_result

        options = AskOptions(
            problem_id=6,
            question="What is the status?",
            limit=10,
            build_index=True,
            no_llm=False,
            llm_cmd="test-llm",
        )
        repo = mock.Mock()
        index = mock.Mock()
        result = _execute_ask_query(options, repo=repo, index=index, repo_root=None)

        mock_ask.assert_called_once_with(
            problem_id=6,
            question="What is the status?",
            repo=repo,
            index=index,
            limit=10,
            build_index_flag=True,
            no_llm=False,
            llm_command="test-llm",
            repo_root=None,
        )
        assert result.success is True

    @mock.patch("erdos.commands.ask.ask_question")
    def test_sets_duration_ms(self, mock_ask: mock.Mock) -> None:
        """Should set duration_ms on result."""
        mock_result = CLIOutput.ok("erdos ask", {"answer": "test"})
        mock_ask.return_value = mock_result

        options = AskOptions(
            problem_id=6,
            question="test",
            limit=5,
            build_index=False,
            no_llm=True,
            llm_cmd=None,
        )
        result = _execute_ask_query(
            options, repo=mock.Mock(), index=mock.Mock(), repo_root=None
        )

        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    @mock.patch("erdos.commands.ask.ask_question")
    def test_handles_none_llm_cmd(self, mock_ask: mock.Mock) -> None:
        """Should handle None llm_cmd."""
        mock_result = CLIOutput.ok("erdos ask", {"answer": "test"})
        mock_ask.return_value = mock_result

        options = AskOptions(
            problem_id=6,
            question="test",
            limit=5,
            build_index=False,
            no_llm=True,
            llm_cmd=None,
        )
        _execute_ask_query(options, repo=mock.Mock(), index=mock.Mock(), repo_root=None)

        mock_ask.assert_called_once()
        assert mock_ask.call_args[1]["llm_command"] is None
