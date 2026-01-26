"""End-to-end tests for erdos logs command."""

from __future__ import annotations

import json

import pytest


@pytest.mark.e2e
class TestErdosLogs:
    """E2E tests for erdos logs JSON contract."""

    def test_logs_json_output(self, cli_runner) -> None:
        """erdos --json logs returns valid JSON."""
        # First run a command to generate a log entry
        cli_runner("--json", "list", "--limit", "1")

        # Then check logs
        result = cli_runner("--json", "logs", "--limit", "5")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos logs"

    def test_logs_entries_have_schema_keys(self, cli_runner) -> None:
        """erdos logs entries have expected schema keys."""
        # Generate a log entry
        cli_runner("--json", "list", "--limit", "1")

        result = cli_runner("--json", "logs", "--limit", "5")

        data = json.loads(result.stdout)
        entries = data["data"]["entries"]
        assert isinstance(entries, list)

        if len(entries) > 0:
            entry = entries[0]
            assert "id" in entry
            assert "timestamp" in entry
            assert "command" in entry
            assert "success" in entry

    def test_logs_captures_command_execution(self, cli_runner) -> None:
        """erdos logs captures executed commands."""
        # Run a specific command
        cli_runner("--json", "show", "6")

        # Check it appears in logs
        result = cli_runner("--json", "logs", "--limit", "10")

        data = json.loads(result.stdout)
        entries = data["data"]["entries"]
        commands = [e["command"] for e in entries]
        assert "erdos show" in commands

    def test_logs_exit_code_zero(self, cli_runner) -> None:
        """erdos logs returns exit code 0."""
        result = cli_runner("logs", "--limit", "1")
        assert result.returncode == 0
