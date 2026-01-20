"""Unit tests for ask LLM execution."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from erdos.core.ask import execute_llm
from erdos.core.constants import LLM_COMMAND_TIMEOUT


def test_execute_llm_with_successful_command():
    """execute_llm must run subprocess and capture output."""
    llm_command = "echo 'test answer'"
    prompt = "Test prompt"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="test answer\n",
            returncode=0,
        )

        _answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)

        assert _answer == "test answer\n"
        assert exit_code == 0
        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs["input"] == prompt
        assert call_args.kwargs["text"] is True
        assert call_args.kwargs["capture_output"] is True


def test_execute_llm_with_command_parsing():
    """execute_llm must parse command with shlex.split."""
    llm_command = "python -c 'print(42)'"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="42\n", returncode=0)

        _answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)

        assert exit_code == 0
        # Verify command was split correctly (not shell=True)
        call_args = mock_run.call_args
        assert isinstance(call_args.args[0], list)  # Should be list of args, not string
        assert call_args.kwargs.get("shell") is not True


def test_execute_llm_with_nonzero_exit():
    """execute_llm must return exit code when command fails."""
    llm_command = "false"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="",
            returncode=1,
        )

        _answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)

        assert exit_code == 1


def test_execute_llm_with_stderr_capture():
    """execute_llm must capture stderr separately."""
    llm_command = "some-command"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="output",
            stderr="error message",
            returncode=1,
        )

        _answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)

        assert exit_code == 1
        # stderr should be captured but not mixed with stdout
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs["capture_output"] is True


def test_execute_llm_with_empty_output():
    """execute_llm must handle empty stdout."""
    llm_command = "true"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        _answer, exit_code = execute_llm(llm_command=llm_command, prompt=prompt)

        assert _answer == ""
        assert exit_code == 0


def test_execute_llm_passes_prompt_via_stdin():
    """execute_llm must pass the prompt as stdin to the subprocess."""
    llm_command = "cat"
    prompt = "This is the full prompt text"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=prompt, returncode=0)

        execute_llm(llm_command=llm_command, prompt=prompt)

        call_args = mock_run.call_args
        assert call_args.kwargs["input"] == prompt


def test_execute_llm_raises_on_file_not_found():
    """execute_llm must raise when command executable doesn't exist."""
    llm_command = "/nonexistent/command"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("No such file")

        with pytest.raises(FileNotFoundError):
            execute_llm(llm_command=llm_command, prompt=prompt)


def test_execute_llm_passes_timeout_to_subprocess():
    """execute_llm must pass timeout parameter to subprocess.run."""
    llm_command = "echo 'test'"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test\n", returncode=0)

        execute_llm(llm_command=llm_command, prompt=prompt, timeout=60)

        call_args = mock_run.call_args
        assert call_args.kwargs["timeout"] == 60


def test_execute_llm_uses_default_timeout():
    """execute_llm must use default timeout from constants."""
    llm_command = "echo 'test'"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test\n", returncode=0)

        execute_llm(llm_command=llm_command, prompt=prompt)

        call_args = mock_run.call_args
        assert call_args.kwargs["timeout"] == LLM_COMMAND_TIMEOUT


def test_execute_llm_timeout_can_be_disabled():
    """execute_llm must allow None timeout for no limit."""
    llm_command = "echo 'test'"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test\n", returncode=0)

        execute_llm(llm_command=llm_command, prompt=prompt, timeout=None)

        call_args = mock_run.call_args
        assert call_args.kwargs["timeout"] is None


def test_execute_llm_raises_timeout_expired():
    """execute_llm must raise TimeoutExpired when command times out."""
    llm_command = "sleep 999"
    prompt = "Test"

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 999", timeout=1)

        with pytest.raises(subprocess.TimeoutExpired):
            execute_llm(llm_command=llm_command, prompt=prompt, timeout=1)
