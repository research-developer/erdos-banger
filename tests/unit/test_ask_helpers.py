"""Unit tests for ask_question helper functions."""

from unittest.mock import MagicMock, patch

from erdos.core.ask import _ensure_index_ready, _execute_llm_if_enabled
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex


def test_ensure_index_ready_no_build():
    """_ensure_index_ready returns index when no build requested."""

    mock_loader = MagicMock(spec=ProblemLoader)

    with patch("erdos.core.ask.SearchIndex.from_default") as mock_from_default:
        mock_index = MagicMock(spec=SearchIndex)
        mock_from_default.return_value = mock_index

        result = _ensure_index_ready(loader=mock_loader, build_index_flag=False)

        assert isinstance(result, SearchIndex)
        assert result == mock_index
        mock_from_default.assert_called_once()


def test_ensure_index_ready_with_build():
    """_ensure_index_ready builds index when requested."""
    mock_loader = MagicMock(spec=ProblemLoader)

    with (
        patch("erdos.core.ask.build_index") as mock_build_index,
        patch("erdos.core.ask.SearchIndex.from_default") as mock_from_default,
    ):
        mock_index = MagicMock(spec=SearchIndex)
        mock_from_default.return_value = mock_index

        result = _ensure_index_ready(loader=mock_loader, build_index_flag=True)

        assert isinstance(result, SearchIndex)
        mock_build_index.assert_called_once_with(loader=mock_loader, rebuild=True)
        mock_from_default.assert_called_once()


def test_ensure_index_ready_build_error():
    """_ensure_index_ready returns CLIOutput error if build fails."""
    mock_loader = MagicMock(spec=ProblemLoader)

    with patch("erdos.core.ask.build_index") as mock_build_index:
        mock_build_index.side_effect = RuntimeError("Build failed")

        result = _ensure_index_ready(loader=mock_loader, build_index_flag=True)

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "Build failed" in result.error["message"]


def test_ensure_index_ready_index_open_error():
    """_ensure_index_ready returns CLIOutput error if index open fails."""
    mock_loader = MagicMock(spec=ProblemLoader)

    with patch("erdos.core.ask.SearchIndex.from_default") as mock_from_default:
        mock_from_default.side_effect = RuntimeError("Index error")

        result = _ensure_index_ready(loader=mock_loader, build_index_flag=False)

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "Index error" in result.error["message"]


def test_execute_llm_if_enabled_disabled():
    """_execute_llm_if_enabled skips LLM when disabled."""

    result = _execute_llm_if_enabled(
        prompt="Test prompt",
        enable_llm=False,
        llm_command=None,
    )

    assert isinstance(result, dict)
    assert result["answer"] is None
    assert result["llm_exit_code"] is None
    assert result["llm_enabled"] is False
    assert result["llm_command"] is None


def test_execute_llm_if_enabled_no_command():
    """_execute_llm_if_enabled skips LLM when no command available."""

    result = _execute_llm_if_enabled(
        prompt="Test prompt",
        enable_llm=True,
        llm_command=None,
    )

    assert isinstance(result, dict)
    assert result["answer"] is None
    assert result["llm_exit_code"] is None
    assert result["llm_enabled"] is False
    assert result["llm_command"] is None


def test_execute_llm_if_enabled_success():
    """_execute_llm_if_enabled executes LLM successfully."""

    with patch("erdos.core.ask.execute_llm") as mock_execute_llm:
        mock_execute_llm.return_value = ("Answer text", 0)

        result = _execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, dict)
        assert result["answer"] == "Answer text"
        assert result["llm_exit_code"] == 0
        assert result["llm_enabled"] is True
        assert result["llm_command"] == "echo"


def test_execute_llm_if_enabled_nonzero_exit():
    """_execute_llm_if_enabled returns error on nonzero exit code."""

    with patch("erdos.core.ask.execute_llm") as mock_execute_llm:
        mock_execute_llm.return_value = ("Error output", 1)

        result = _execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "exited with code 1" in result.error["message"]


def test_execute_llm_if_enabled_command_not_found():
    """_execute_llm_if_enabled returns error when command not found."""

    with patch("erdos.core.ask.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = FileNotFoundError()

        result = _execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="nonexistent",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error["message"]


def test_execute_llm_if_enabled_os_error():
    """_execute_llm_if_enabled returns error on OS error."""

    with patch("erdos.core.ask.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = OSError("Permission denied")

        result = _execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "error" in result.error["message"].lower()


def test_execute_llm_if_enabled_generic_exception():
    """_execute_llm_if_enabled returns error on unexpected exception."""

    with patch("erdos.core.ask.execute_llm") as mock_execute_llm:
        mock_execute_llm.side_effect = RuntimeError("Unexpected error")

        result = _execute_llm_if_enabled(
            prompt="Test prompt",
            enable_llm=True,
            llm_command="echo",
        )

        assert isinstance(result, CLIOutput)
        assert not result.success
        assert result.error is not None
        assert "failed" in result.error["message"].lower()
