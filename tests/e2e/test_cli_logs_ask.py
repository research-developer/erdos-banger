"""End-to-end tests for `erdos logs ask` command."""

from __future__ import annotations

import json

import pytest


@pytest.mark.e2e
class TestErdosLogsAsk:
    """E2E tests for ask log querying."""

    def test_logs_ask_json_output(self, cli_runner) -> None:
        """`erdos --json logs ask` returns valid JSON."""
        cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        result = cli_runner("--json", "logs", "ask", "--problem", "6", "--limit", "5")
        data = json.loads(result.stdout)

        assert data["success"] is True
        assert data["command"] == "erdos logs ask"
        assert data["data"]["problem_id"] == 6

    def test_logs_ask_returns_entries_with_full_schema(self, cli_runner) -> None:
        """`erdos logs ask` returns entries with expected schema keys."""
        cli_runner("--json", "ask", "6", "What is known?", "--no-llm")

        result = cli_runner("--json", "logs", "ask", "--problem", "6", "--limit", "5")
        data = json.loads(result.stdout)
        entries = data["data"]["entries"]
        assert isinstance(entries, list)
        assert len(entries) >= 1

        entry = entries[-1]
        assert entry["problem_id"] == 6
        assert "timestamp" in entry
        assert entry["question"] == "What is known?"
        assert entry["answer"] is None
        assert entry["llm"]["enabled"] is False
