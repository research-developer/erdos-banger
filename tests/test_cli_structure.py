"""Verify CLI structure is correct."""

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


def test_cli_has_version_flag() -> None:
    """CLI should have --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "erdos-harness" in result.stdout


def test_cli_has_json_flag() -> None:
    """CLI should have global --json flag."""
    result = runner.invoke(app, ["--help"])
    assert "--json" in result.stdout


def test_cli_has_required_commands() -> None:
    """CLI should have all v1 commands."""
    result = runner.invoke(app, ["--help"])

    required_commands = ["list", "show", "refs", "search", "lean"]
    for cmd in required_commands:
        assert cmd in result.stdout, f"Missing command: {cmd}"


def test_lean_has_subcommands() -> None:
    """lean command should have init, check, formalize subcommands."""
    result = runner.invoke(app, ["lean", "--help"])

    subcommands = ["init", "check", "formalize"]
    for cmd in subcommands:
        assert cmd in result.stdout, f"Missing lean subcommand: {cmd}"
