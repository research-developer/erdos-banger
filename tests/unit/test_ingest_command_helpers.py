"""Unit tests for ingest command helper functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch


if TYPE_CHECKING:
    import pytest

from erdos.commands.ingest import (
    IngestOptions,
    _get_repo_root,
    _prepare_ingest_options,
    _run_ingestion,
    _show_progress_message,
)


def test_get_repo_root_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _get_repo_root uses ERDOS_REPO_ROOT env var if set."""
    test_path = "/test/repo/root"
    monkeypatch.setenv("ERDOS_REPO_ROOT", test_path)

    result = _get_repo_root()

    assert result == Path(test_path)


def test_get_repo_root_defaults_to_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _get_repo_root defaults to cwd if env var not set."""
    monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)

    result = _get_repo_root()

    assert result == Path.cwd()


def test_prepare_ingest_options_with_mailto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _prepare_ingest_options uses provided mailto."""
    monkeypatch.delenv("ERDOS_MAILTO", raising=False)
    monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)

    mailto, repo_root = _prepare_ingest_options("user@example.com")

    assert mailto == "user@example.com"
    assert repo_root == Path.cwd()


def test_prepare_ingest_options_without_mailto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _prepare_ingest_options uses env var when mailto empty."""
    monkeypatch.setenv("ERDOS_MAILTO", "env@example.com")
    monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)

    mailto, repo_root = _prepare_ingest_options("")

    assert mailto == "env@example.com"
    assert repo_root == Path.cwd()


def test_prepare_ingest_options_default_mailto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test _prepare_ingest_options uses default when no mailto provided."""
    monkeypatch.delenv("ERDOS_MAILTO", raising=False)
    monkeypatch.delenv("ERDOS_REPO_ROOT", raising=False)

    mailto, repo_root = _prepare_ingest_options("")

    assert mailto == "erdos-banger@example.com"
    assert repo_root == Path.cwd()


def test_show_progress_message_in_json_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _show_progress_message is silent in JSON mode."""
    _show_progress_message(6, json_output=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_show_progress_message_in_human_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test _show_progress_message shows output in human mode."""
    _show_progress_message(6, json_output=False)

    captured = capsys.readouterr()
    assert "Problem 6" in captured.err


def test_ingest_options_dataclass() -> None:
    """Test IngestOptions dataclass with default values."""
    options = IngestOptions(problem_id=6)

    assert options.problem_id == 6
    assert options.force is False
    assert options.no_download is False
    assert options.no_network is False
    assert options.timeout == 30.0
    assert options.delay == 3.0
    assert options.mailto == ""
    assert options.json_output is False


def test_ingest_options_with_all_values() -> None:
    """Test IngestOptions dataclass with all values set."""
    options = IngestOptions(
        problem_id=42,
        force=True,
        no_download=True,
        no_network=True,
        timeout=60.0,
        delay=5.0,
        mailto="test@example.com",
        json_output=True,
    )

    assert options.problem_id == 42
    assert options.force is True
    assert options.no_download is True
    assert options.no_network is True
    assert options.timeout == 60.0
    assert options.delay == 5.0
    assert options.mailto == "test@example.com"
    assert options.json_output is True


@patch("erdos.commands.ingest.ingest_problem_references")
@patch("erdos.commands.ingest._show_progress_message")
def test_run_ingestion_calls_core_logic(
    _mock_progress: MagicMock,
    mock_ingest: MagicMock,
    tmp_path: Path,
) -> None:
    """Test _run_ingestion calls core ingestion logic."""
    # Setup
    options = IngestOptions(
        problem_id=6,
        force=True,
        no_download=True,
        no_network=False,
        timeout=30.0,
        delay=3.0,
        mailto="test@example.com",
        json_output=False,
    )
    mock_result = MagicMock()
    mock_result.duration_ms = None
    mock_ingest.return_value = mock_result

    # Execute
    result = _run_ingestion(options, tmp_path, "test@example.com")

    # Verify progress message was called
    _mock_progress.assert_called_once_with(6, False)

    # Verify core logic was called
    mock_ingest.assert_called_once_with(
        6,
        repo_root=tmp_path,
        force=True,
        no_download=True,
        no_network=False,
        timeout=30.0,
        delay=3.0,
        mailto="test@example.com",
    )
    assert result is mock_result
    assert result.duration_ms is not None
    assert isinstance(result.duration_ms, (int, float))


@patch("erdos.commands.ingest.ingest_problem_references")
@patch("erdos.commands.ingest._show_progress_message")
def test_run_ingestion_sets_duration(
    _mock_progress: MagicMock,
    mock_ingest: MagicMock,
    tmp_path: Path,
) -> None:
    """Test _run_ingestion sets duration_ms on result."""
    options = IngestOptions(problem_id=6)
    mock_result = MagicMock()
    mock_result.duration_ms = None
    mock_ingest.return_value = mock_result

    result = _run_ingestion(options, tmp_path, "test@example.com")

    assert hasattr(result, "duration_ms")
    assert result.duration_ms is not None
    assert result.duration_ms >= 0
