"""Tests for sync statements command (SPEC-035)."""

from collections.abc import Callable
from io import StringIO
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from erdos.cli import app
from erdos.commands.sync.statements_cmd import _print_human


runner = CliRunner()


def test_sync_statements_help(strip_ansi: Callable[[str], str]) -> None:
    """Verify statements command shows help."""
    result = runner.invoke(app, ["sync", "statements", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "Sync Lean statement from DeepMind" in output
    assert "--force" in output
    assert "--dry-run" in output
    assert "--no-network" in output


def test_sync_statements_requires_problem_id(strip_ansi: Callable[[str], str]) -> None:
    """Verify statements command requires problem ID."""
    result = runner.invoke(app, ["sync", "statements"])
    output = strip_ansi(result.output)
    assert result.exit_code != 0
    assert "Missing argument 'PROBLEM_ID'" in output


def test_sync_statements_shows_skip_lean_validation(
    strip_ansi: Callable[[str], str],
) -> None:
    """Verify statements command shows --skip-lean-validation flag."""
    result = runner.invoke(app, ["sync", "statements", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--skip-lean-validation" in output


def test_sync_statements_shows_path_option(strip_ansi: Callable[[str], str]) -> None:
    """Verify statements command shows --path option."""
    result = runner.invoke(app, ["sync", "statements", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--path" in output


class TestPrintHuman:
    """Tests for _print_human function."""

    def test_print_human_dry_run(self) -> None:
        """Test dry run output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "problem_id": 347,
            "dry_run": True,
            "path": "/path/to/file.lean",
        }
        with patch("erdos.commands.sync.statements_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "Would import" in text
        assert "347" in text

    def test_print_human_written(self) -> None:
        """Test written output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "problem_id": 347,
            "written": True,
            "path": "/path/to/file.lean",
        }
        with patch("erdos.commands.sync.statements_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "Imported" in text
        assert "347" in text

    def test_print_human_already_imported(self) -> None:
        """Test already imported output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "problem_id": 347,
            "written": False,
            "reason": "already_imported",
        }
        with patch("erdos.commands.sync.statements_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "Up to date" in text
        assert "347" in text

    def test_print_human_fallback(self) -> None:
        """Test fallback output when no specific reason."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "problem_id": 347,
            "written": False,
        }
        with patch("erdos.commands.sync.statements_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "347" in text
        assert "JSON output" in text
