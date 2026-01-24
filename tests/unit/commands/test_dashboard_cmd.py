"""Unit tests for erdos dashboard command (SPEC-034)."""

from __future__ import annotations

import json
from pathlib import Path

from erdos.cli import app
from erdos.core.research.models import AttemptResult, LeadStatus
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.workspace import ensure_problem_workspace
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


class TestDashboardCommand:
    """Tests for erdos dashboard command."""

    def test_dashboard_empty_workspace(self, tmp_path: Path) -> None:
        """Dashboard works with empty research workspace."""
        result = runner.invoke(
            app,
            ["dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        # Should not crash
        assert result.exit_code == 0

    def test_dashboard_json_mode_empty(self, tmp_path: Path) -> None:
        """JSON mode outputs valid CLIOutput envelope for empty data."""
        result = runner.invoke(
            app,
            ["--json", "dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

    def test_dashboard_json_mode_with_data(self, tmp_path: Path) -> None:
        """JSON mode outputs complete dashboard snapshot."""
        # Setup research workspace with data
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Test Lead", status=LeadStatus.NEW)
        store.attempt_log(6, result=AttemptResult.FAILED, summary="Test attempt")

        result = runner.invoke(
            app,
            ["--json", "dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True
        assert "problems" in data["data"]
        assert len(data["data"]["problems"]) == 1
        assert data["data"]["problems"][0]["problem_id"] == 6

    def test_dashboard_json_mode_is_non_interactive(self, tmp_path: Path) -> None:
        """JSON mode must not enter interactive loop."""
        # This test just verifies the command exits cleanly
        # without hanging in an interactive loop
        result = runner.invoke(
            app,
            ["--json", "dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        # Output must be valid JSON (not mixed with interactive elements)
        json.loads(result.stdout)

    def test_dashboard_problems_filter(self, tmp_path: Path) -> None:
        """--problems filter limits to specific problem IDs."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        ensure_problem_workspace(42, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Lead 6")
        store.lead_add(42, title="Lead 42")

        result = runner.invoke(
            app,
            ["--json", "dashboard", "--problems", "6"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["data"]["problems"]) == 1
        assert data["data"]["problems"][0]["problem_id"] == 6

    def test_dashboard_recent_filter(self, tmp_path: Path) -> None:
        """--recent filter applies time window."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Recent Lead")

        result = runner.invoke(
            app,
            ["--json", "dashboard", "--recent", "7d"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["success"] is True

    def test_dashboard_problem_detail(self, tmp_path: Path) -> None:
        """--problem starts in problem detail view (JSON mode)."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Test Lead")

        result = runner.invoke(
            app,
            ["--json", "dashboard", "--problem", "6"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Should show detail for problem 6
        assert data["success"] is True
        # In detail mode, the data should focus on one problem
        assert "problem" in data["data"] or "problems" in data["data"]


class TestDashboardCommandValidation:
    """Tests for CLI option validation."""

    def test_invalid_recent_format(self, tmp_path: Path) -> None:
        """Invalid --recent format returns error."""
        result = runner.invoke(
            app,
            ["dashboard", "--recent", "invalid"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code != 0

    def test_invalid_problems_format(self, tmp_path: Path) -> None:
        """Invalid --problems format returns error."""
        result = runner.invoke(
            app,
            ["dashboard", "--problems", "not,numbers"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        assert result.exit_code != 0


class TestDashboardOutputContract:
    """Tests for JSON output schema contract."""

    def test_json_output_has_required_fields(self, tmp_path: Path) -> None:
        """JSON output contains all required DashboardData fields."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Lead")
        store.attempt_log(6, result=AttemptResult.SUCCESS, summary="Success")

        result = runner.invoke(
            app,
            ["--json", "dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        data = json.loads(result.stdout)["data"]

        # All required fields from DashboardData.to_dict()
        assert "problems" in data
        assert "total_attempts" in data
        assert "total_successes" in data
        assert "overall_success_rate" in data
        assert "active_leads" in data
        assert "active_hypotheses" in data
        assert "open_tasks" in data
        assert "attempt_timeline" in data
        assert "generated_at" in data

    def test_json_output_problem_stats_fields(self, tmp_path: Path) -> None:
        """Each problem in JSON output has required ProblemStats fields."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        store.lead_add(6, title="Lead")

        result = runner.invoke(
            app,
            ["--json", "dashboard"],
            env={"ERDOS_REPO_ROOT": str(tmp_path)},
        )
        problem = json.loads(result.stdout)["data"]["problems"][0]

        assert "problem_id" in problem
        assert "status" in problem
        assert "lead_count" in problem
        assert "hypothesis_count" in problem
        assert "task_count" in problem
        assert "attempt_count" in problem
        assert "success_count" in problem
        assert "success_rate" in problem
        assert "last_activity" in problem
