"""End-to-end tests for erdos show command."""

import json

import pytest


@pytest.mark.e2e
class TestErdosShow:
    def test_show_json_output(self, cli_runner) -> None:
        """erdos --json show outputs valid JSON."""
        result = cli_runner("--json", "show", "6")

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["command"] == "erdos show"
        assert data["data"]["id"] == 6

    def test_show_human_output(self, cli_runner) -> None:
        """erdos show outputs human-readable text by default."""
        result = cli_runner("show", "6")

        assert "Problem 6" in result.stdout
        assert result.returncode == 0

    def test_show_not_found(self, cli_runner) -> None:
        """erdos show returns code 3 for missing problem."""
        result = cli_runner("show", "99999", check=False)

        assert result.returncode == 3

    def test_show_json_not_found(self, cli_runner) -> None:
        """erdos --json show returns error object for missing problem."""
        result = cli_runner("--json", "show", "99999", check=False)

        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error"]["type"] == "NotFoundError"
        assert data["error"]["code"] == 3

    def test_show_invalid_id(self, cli_runner) -> None:
        """erdos show rejects invalid problem ID."""
        result = cli_runner("show", "abc", check=False)

        assert result.returncode == 2  # Usage error

    def test_show_help(self, cli_runner, strip_ansi) -> None:
        """erdos show --help shows usage."""
        result = cli_runner("show", "--help")

        output = strip_ansi(result.stdout)
        assert "Problem ID to display" in output
        assert result.returncode == 0
