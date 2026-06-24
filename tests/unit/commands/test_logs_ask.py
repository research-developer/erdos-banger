"""Unit tests for `erdos logs ask` command helpers."""

from __future__ import annotations

from pathlib import Path

from erdos.commands.logs_ask import query_ask_logs
from erdos.core.ask.logging import log_ask_interaction


def test_query_ask_logs_reads_entries_from_default_location(
    tmp_path: Path, monkeypatch
) -> None:
    """query_ask_logs should read from logs/ask under the data home."""
    monkeypatch.setenv("ERDOS_HOME", str(tmp_path))

    log_ask_interaction(
        problem_id=6,
        question="What is known?",
        answer=None,
        sources=[],
        llm_enabled=False,
    )

    result = query_ask_logs(problem_id=6, limit=5)
    assert result.success is True
    assert result.command == "erdos logs ask"
    assert result.data["problem_id"] == 6
    assert len(result.data["entries"]) == 1


def test_query_ask_logs_invalid_since_returns_usage_error() -> None:
    """Invalid `--since` values should return UsageError (code 2)."""
    result = query_ask_logs(problem_id=6, limit=5, since="not-a-time-spec")
    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "UsageError"
    assert result.error["code"] == 2
