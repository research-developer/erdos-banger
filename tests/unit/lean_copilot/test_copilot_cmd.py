"""Unit tests for erdos lean copilot command (SPEC-033).

Tests:
- Command registration
- Error handling for missing dependencies
- CLI options parsing

These tests do NOT require the copilot extra to be installed.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


class TestCopilotCommandRegistration:
    """Tests for copilot command registration."""

    def test_copilot_subcommand_exists(self):
        """The 'erdos lean copilot' subcommand group is registered."""
        result = runner.invoke(app, ["lean", "--help"])
        assert result.exit_code == 0
        assert "copilot" in result.output

    def test_copilot_serve_exists(self):
        """The 'erdos lean copilot serve' command is registered."""
        result = runner.invoke(app, ["lean", "copilot", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.output

    def test_copilot_serve_help(self):
        """The 'erdos lean copilot serve --help' shows options."""
        result = runner.invoke(app, ["lean", "copilot", "serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
        assert "--host" in result.output
        assert "--llm-cmd" in result.output
        assert "--log-level" in result.output


class TestCopilotServeDependencyCheck:
    """Tests for copilot serve dependency checking."""

    def test_serve_without_copilot_extra_fails_human(self, monkeypatch):
        """Serve fails gracefully when copilot extra is not installed (human)."""
        # Mock is_copilot_available to return False
        monkeypatch.setattr(
            "erdos.lean_copilot.is_copilot_available",
            lambda: False,
        )

        result = runner.invoke(app, ["lean", "copilot", "serve"])

        # Should fail with informative message
        assert result.exit_code != 0
        assert "copilot" in result.output.lower()

    def test_serve_without_copilot_extra_fails_json(self, monkeypatch):
        """Serve fails gracefully when copilot extra is not installed (JSON)."""
        # Mock is_copilot_available to return False
        monkeypatch.setattr(
            "erdos.lean_copilot.is_copilot_available",
            lambda: False,
        )

        result = runner.invoke(app, ["--json", "lean", "copilot", "serve"])

        # Should fail with JSON error
        assert result.exit_code != 0
        output = json.loads(result.output)
        assert output["success"] is False
        assert "DEPENDENCY_ERROR" in output["error"]["type"]
        assert "copilot" in output["error"]["message"].lower()


class TestCopilotServeOptions:
    """Tests for copilot serve command options."""

    def test_default_port(self):
        """Default port is 8000."""
        result = runner.invoke(app, ["lean", "copilot", "serve", "--help"])
        assert "8000" in result.output

    def test_default_host(self):
        """Default host is 127.0.0.1."""
        result = runner.invoke(app, ["lean", "copilot", "serve", "--help"])
        assert "127.0.0.1" in result.output
