"""Verify CLI structure is correct."""

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def test_cli_has_version_flag() -> None:
    """CLI should have --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "erdos-banger" in result.stdout


def test_cli_has_json_flag() -> None:
    """CLI should have global --json flag."""
    result = runner.invoke(app, ["--json", "--help"])
    assert result.exit_code == 0


def test_cli_has_required_commands(strip_ansi) -> None:
    """CLI should have all v1 commands."""
    result = runner.invoke(app, ["--help"])
    output = strip_ansi(result.stdout)

    required_commands = ["list", "show", "refs", "search", "lean"]
    for cmd in required_commands:
        assert cmd in output, f"Missing command: {cmd}"


def test_lean_has_subcommands(strip_ansi) -> None:
    """lean command should have init, check, formalize subcommands."""
    result = runner.invoke(app, ["lean", "--help"])
    output = strip_ansi(result.stdout)

    subcommands = ["init", "check", "formalize"]
    for cmd in subcommands:
        assert cmd in output, f"Missing lean subcommand: {cmd}"
