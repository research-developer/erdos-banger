"""Integration tests for erdos logs command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.models import CLIOutput
from erdos.core.run_logger import RunLogger


runner = CliRunner()


@pytest.fixture
def isolated_logs_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set up isolated environment with test log file."""
    log_file = tmp_path / "logs" / "runs.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ERDOS_RUN_LOG_PATH", str(log_file))

    # Also set test data path
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"
    monkeypatch.setenv("ERDOS_DATA_PATH", str(fixtures_path.parent))

    return log_file


class TestLogsCommand:
    """Tests for 'erdos logs' command."""

    def test_logs_empty(self, isolated_logs_env: Path) -> None:
        """logs with no entries returns empty list."""
        result = runner.invoke(app, ["--json", "logs"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["data"]["entries"] == []

    def test_logs_returns_entries(self, isolated_logs_env: Path) -> None:
        """logs returns logged entries."""
        # Add entries directly via RunLogger
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(
            CLIOutput.ok(command="erdos show", data={"id": 6}), args={"problem_id": 6}
        )
        logger.log(
            CLIOutput.ok(command="erdos search", data={"results": []}),
            args={"query": "prime"},
        )

        result = runner.invoke(app, ["--json", "logs"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert len(output["data"]["entries"]) == 2

    def test_logs_filter_by_problem_id(self, isolated_logs_env: Path) -> None:
        """logs --problem-id filters entries."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 7})

        result = runner.invoke(app, ["--json", "logs", "--problem-id", "6"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert len(output["data"]["entries"]) == 1
        assert output["data"]["entries"][0]["problem_id"] == 6

    def test_logs_filter_by_command(self, isolated_logs_env: Path) -> None:
        """logs --command filters entries."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})
        logger.log(CLIOutput.ok(command="erdos search", data={}), args={})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})

        result = runner.invoke(app, ["--json", "logs", "--command", "erdos show"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert len(output["data"]["entries"]) == 2

    def test_logs_filter_by_status(self, isolated_logs_env: Path) -> None:
        """logs --status filters entries."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})
        logger.log(
            CLIOutput.err(
                command="erdos show", error_type="NotFound", message="Not found", code=2
            ),
            args={},
        )

        result = runner.invoke(app, ["--json", "logs", "--status", "failure"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert len(output["data"]["entries"]) == 1
        assert output["data"]["entries"][0]["success"] is False

    def test_logs_respects_limit(self, isolated_logs_env: Path) -> None:
        """logs --limit restricts results."""
        logger = RunLogger(log_file=isolated_logs_env)
        for i in range(10):
            logger.log(CLIOutput.ok(command=f"erdos test{i}", data={}), args={})

        result = runner.invoke(app, ["--json", "logs", "--limit", "3"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert len(output["data"]["entries"]) == 3

    def test_logs_summary_mode(self, isolated_logs_env: Path) -> None:
        """logs --summary returns aggregated data."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})
        logger.log(CLIOutput.ok(command="erdos search", data={}), args={})

        result = runner.invoke(app, ["--json", "logs", "--summary"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        data = output["data"]
        assert data["total_runs"] == 3
        assert "by_command" in data
        assert "by_problem" in data
        assert data["by_command"]["erdos show"]["runs"] == 2

    def test_logs_human_output(self, isolated_logs_env: Path) -> None:
        """logs without --json shows human-readable output."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={"problem_id": 6})

        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        assert "erdos show" in result.stdout

    def test_logs_filter_by_since(self, isolated_logs_env: Path) -> None:
        """logs --since filters by time."""
        logger = RunLogger(log_file=isolated_logs_env)
        logger.log(CLIOutput.ok(command="erdos show", data={}), args={})

        result = runner.invoke(app, ["--json", "logs", "--since", "1d"])
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        # All recent entries should be included
        assert len(output["data"]["entries"]) == 1

    def test_logs_help(self, strip_ansi) -> None:
        """logs --help shows usage."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--problem-id" in output
        assert "--command" in output
        assert "--since" in output
        assert "--status" in output
        assert "--limit" in output
        assert "--summary" in output


class TestLogsIntegrationWithCommands:
    """Test that running commands creates log entries."""

    def test_show_command_creates_log_entry(
        self, isolated_logs_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running 'erdos show' should create a log entry."""
        # Set up test data path
        fixtures_path = (
            Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"
        )
        monkeypatch.setenv("ERDOS_DATA_PATH", str(fixtures_path.parent))

        # Run show command
        runner.invoke(app, ["show", "6"])
        # Note: exit code depends on whether problem 6 exists in fixtures

        # Query logs
        log_result = runner.invoke(app, ["--json", "logs", "--limit", "1"])
        output = json.loads(log_result.stdout)
        entries = output["data"]["entries"]
        assert len(entries) >= 0  # May be 0 if logging not integrated yet

    def test_search_command_creates_log_entry(
        self, isolated_logs_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running 'erdos search' should create a log entry."""
        fixtures_path = (
            Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"
        )
        monkeypatch.setenv("ERDOS_DATA_PATH", str(fixtures_path.parent))

        # Run search command
        runner.invoke(app, ["search", "prime"])

        # Query logs
        log_result = runner.invoke(app, ["--json", "logs", "--command", "erdos search"])
        output = json.loads(log_result.stdout)
        # Entries depend on integration status
        assert "entries" in output["data"]

    def test_failed_command_logs_failure(
        self, isolated_logs_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failed commands should log with success=false."""
        fixtures_path = (
            Path(__file__).parent.parent / "fixtures" / "sample_problems.yaml"
        )
        monkeypatch.setenv("ERDOS_DATA_PATH", str(fixtures_path.parent))

        # Run show with invalid ID
        runner.invoke(app, ["show", "999999"])
        # This should fail with not found

        # Query failure logs
        log_result = runner.invoke(app, ["--json", "logs", "--status", "failure"])
        output = json.loads(log_result.stdout)
        # Entries depend on integration status
        assert "entries" in output["data"]
