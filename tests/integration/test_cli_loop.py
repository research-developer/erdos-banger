"""Integration tests for the loop command."""

import json
from pathlib import Path

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


class TestLoopRunCommand:
    """Test erdos loop run command."""

    def test_help_shows_usage(self, strip_ansi) -> None:
        result = runner.invoke(app, ["loop", "run", "--help"])
        assert result.exit_code == 0
        assert "Run iterative proof loop for a problem" in strip_ansi(result.stdout)

    def test_missing_problem_id(self) -> None:
        result = runner.invoke(app, ["loop", "run"])
        assert result.exit_code != 0
        # Error message may be in stdout or stderr depending on typer version
        output = result.stdout or result.output or ""
        assert "Missing argument" in output or "PROBLEM_ID" in output

    def test_invalid_problem_id_not_found(self) -> None:
        result = runner.invoke(app, ["loop", "run", "99999", "--no-apply"])
        # Should fail because problem doesn't exist
        assert result.exit_code != 0

    def test_no_apply_mode_with_path(self, tmp_path: Path) -> None:
        """--no-apply mode accepts --path option."""
        project_path = tmp_path / "formal" / "lean"

        # Just verify the options are accepted
        result = runner.invoke(
            app,
            [
                "loop",
                "run",
                "6",
                "--no-apply",
                "--path",
                str(project_path),
            ],
        )
        # LLM_REQUIRED or similar status - we just check it runs
        assert result.exit_code in (0, 1)  # Either success or expected failure

    def test_json_output(self) -> None:
        """Test JSON output mode."""
        result = runner.invoke(
            app,
            [
                "--json",
                "loop",
                "run",
                "99999",  # Non-existent problem
                "--no-apply",
            ],
        )
        # Should return JSON even on error
        assert result.exit_code != 0
        # Output should be valid JSON structure
        output = json.loads(result.stdout)
        assert "command" in output
        assert output["command"] == "erdos loop"

    def test_llm_cmd_option_accepted(self, strip_ansi) -> None:
        """Test --llm-cmd option is accepted."""
        # Use --help to verify the option exists without actually running
        result = runner.invoke(
            app,
            [
                "loop",
                "run",
                "--help",
            ],
        )
        assert "--llm-cmd" in strip_ansi(result.stdout)

    def test_config_options(self) -> None:
        """Test configuration options are accepted."""
        result = runner.invoke(
            app,
            [
                "loop",
                "run",
                "6",
                "--max-iter",
                "5",
                "--timeout",
                "60",
                "--allow-sorry-increase",
                "1",
                "--max-patch-lines",
                "25",
                "--max-patch-bytes",
                "4096",
                "--rag-limit",
                "3",
                "--no-apply",
                "--help",
            ],
        )
        assert result.exit_code == 0


class TestLoopHelpCommand:
    """Test erdos loop help."""

    def test_loop_help(self) -> None:
        result = runner.invoke(app, ["loop", "--help"])
        assert result.exit_code == 0
        assert "Iterative Lean proof loop" in result.stdout
        assert "run" in result.stdout
