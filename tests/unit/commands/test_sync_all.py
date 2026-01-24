"""Tests for sync all command (SPEC-035)."""

from collections.abc import Callable
from io import StringIO
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from erdos.cli import app
from erdos.commands.sync.all_cmd import _print_human, _print_step_result
from erdos.core.models import CLIOutput


runner = CliRunner()


def test_sync_all_help(strip_ansi: Callable[[str], str]) -> None:
    """Verify sync all command shows help."""
    result = runner.invoke(app, ["sync", "all", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "Run all sync operations in sequence" in output
    assert "--problems" in output
    assert "--skip-submodule" in output
    assert "--skip-website" in output
    assert "--skip-proof" in output
    assert "--skip-statements" in output


def test_sync_all_skip_all_no_network() -> None:
    """Verify sync all with all skips and no-network works."""
    result = runner.invoke(
        app,
        [
            "--json",
            "sync",
            "all",
            "--skip-submodule",
            "--skip-website",
            "--skip-proof",
            "--skip-statements",
        ],
    )
    assert result.exit_code == 0
    assert '"success": true' in result.output


def test_sync_all_invalid_problem_ids() -> None:
    """Verify sync all rejects invalid problem IDs."""
    result = runner.invoke(
        app,
        [
            "--json",
            "sync",
            "all",
            "--skip-submodule",
            "--skip-website",
            "--skip-proof",
            "--skip-statements",
            "--problems",
            "abc,def",
        ],
    )
    assert result.exit_code != 0
    assert "Invalid problem ID" in result.output


def test_sync_all_shows_force_flag(strip_ansi: Callable[[str], str]) -> None:
    """Verify sync all shows --force flag."""
    result = runner.invoke(app, ["sync", "all", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--force" in output


def test_sync_all_shows_no_network_flag(strip_ansi: Callable[[str], str]) -> None:
    """Verify sync all shows --no-network flag."""
    result = runner.invoke(app, ["sync", "all", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--no-network" in output


def test_sync_all_shows_lean_path_flag(strip_ansi: Callable[[str], str]) -> None:
    """Verify sync all shows --lean-path flag."""
    result = runner.invoke(app, ["sync", "all", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--lean-path" in output


def test_sync_all_orchestrates_website_and_proof_steps() -> None:
    """Verify sync all calls website + proof steps when problems are provided."""
    with (
        patch("erdos.commands.sync.all_cmd.sync_website_problem") as mock_website,
        patch("erdos.commands.sync.all_cmd.sync_proof_links") as mock_proof,
    ):
        mock_website.side_effect = [
            CLIOutput.ok(
                command="erdos sync website",
                data={"problem_id": 6, "updated": True},
            ),
            CLIOutput.ok(
                command="erdos sync website",
                data={"problem_id": 347, "updated": False},
            ),
        ]
        mock_proof.side_effect = [
            CLIOutput.ok(
                command="erdos sync proof",
                data={"problem_id": 6, "links_count": 1},
            ),
            CLIOutput.ok(
                command="erdos sync proof",
                data={"problem_id": 347, "links_count": 0},
            ),
        ]

        result = runner.invoke(
            app,
            [
                "--json",
                "sync",
                "all",
                "--problems",
                "6,347",
                "--dry-run",
                "--skip-submodule",
                "--skip-statements",
            ],
        )

    assert result.exit_code == 0
    assert '"success": true' in result.output
    assert mock_website.call_count == 2
    assert mock_proof.call_count == 2


class TestPrintStepResult:
    """Tests for _print_step_result helper function."""

    def test_step_result_error(self) -> None:
        """Test error step output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {"success": False, "error": "Connection failed"}
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Test", step_data)
        text = output.getvalue()
        assert "Test" in text
        assert "Connection failed" in text

    def test_step_result_skipped(self) -> None:
        """Test skipped step output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {
            "success": True,
            "skipped": True,
            "reason": "no_network",
        }
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Test", step_data)
        text = output.getvalue()
        assert "Test" in text
        assert "skipped" in text

    def test_step_result_submodule_updated(self) -> None:
        """Test submodule updated output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {
            "success": True,
            "updated": True,
            "old_commit": "abc12345",
            "new_commit": "def67890",
        }
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Submodule", step_data)
        text = output.getvalue()
        assert "Submodule" in text
        assert "abc12345" in text
        assert "def67890" in text

    def test_step_result_submodule_up_to_date(self) -> None:
        """Test submodule up to date output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {
            "success": True,
            "updated": False,
            "commit": "abc12345",
        }
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Submodule", step_data)
        text = output.getvalue()
        assert "Submodule" in text
        assert "up to date" in text

    def test_step_result_website(self) -> None:
        """Test website step output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {"success": True, "fetched": 5}
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Website", step_data)
        text = output.getvalue()
        assert "Website" in text
        assert "5" in text

    def test_step_result_proof(self) -> None:
        """Test proof step output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {"success": True, "proofs_found": 3}
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Proof", step_data)
        text = output.getvalue()
        assert "Proof" in text
        assert "3" in text

    def test_step_result_statements(self) -> None:
        """Test statements step output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        step_data: dict[str, Any] = {"success": True, "imported": 2, "skipped_count": 1}
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_step_result("Statements", step_data)
        text = output.getvalue()
        assert "Statements" in text
        assert "2 imported" in text


class TestPrintHuman:
    """Tests for _print_human function."""

    def test_print_human_success(self) -> None:
        """Test successful sync output."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "submodule": {"success": True, "skipped": True, "reason": "skip_flag"},
            "website": {"success": True, "skipped": True, "reason": "skip_flag"},
            "proof": {"success": True, "skipped": True, "reason": "skip_flag"},
            "statements": {"success": True, "skipped": True, "reason": "skip_flag"},
            "errors": [],
        }
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "Sync All Results" in text
        assert "completed successfully" in text

    def test_print_human_with_errors(self) -> None:
        """Test sync output with errors."""
        from rich.console import Console

        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)
        data: dict[str, Any] = {
            "submodule": {"success": False, "error": "Failed"},
            "website": {"success": True, "skipped": True, "reason": "skip_flag"},
            "proof": {"success": True, "skipped": True, "reason": "skip_flag"},
            "statements": {"success": True, "skipped": True, "reason": "skip_flag"},
            "errors": ["submodule: Failed"],
        }
        with patch("erdos.commands.sync.all_cmd.console", console):
            _print_human(data)
        text = output.getvalue()
        assert "Sync All Results" in text
        assert "1 error" in text
