"""Unit tests for dashboard data aggregation (SPEC-034)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from erdos.core.dashboard.data import (
    DashboardData,
    ProblemStats,
    aggregate_dashboard_data,
)
from erdos.core.research.models import (
    AttemptResult,
    HypothesisStatus,
    LeadStatus,
    TaskStatus,
)
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.workspace import ensure_problem_workspace


class TestProblemStats:
    """Tests for ProblemStats model."""

    def test_problem_stats_creation(self) -> None:
        stats = ProblemStats(
            problem_id=6,
            status="active",
            lead_count=3,
            hypothesis_count=2,
            task_count=5,
            attempt_count=10,
            success_count=1,
            last_activity=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        assert stats.problem_id == 6
        assert stats.status == "active"
        assert stats.lead_count == 3
        assert stats.hypothesis_count == 2
        assert stats.task_count == 5
        assert stats.attempt_count == 10
        assert stats.success_count == 1
        assert stats.last_activity is not None

    def test_problem_stats_success_rate(self) -> None:
        stats = ProblemStats(
            problem_id=6,
            status="active",
            lead_count=0,
            hypothesis_count=0,
            task_count=0,
            attempt_count=10,
            success_count=2,
            last_activity=None,
        )
        assert stats.success_rate == 20.0

    def test_problem_stats_success_rate_no_attempts(self) -> None:
        stats = ProblemStats(
            problem_id=6,
            status="new",
            lead_count=0,
            hypothesis_count=0,
            task_count=0,
            attempt_count=0,
            success_count=0,
            last_activity=None,
        )
        assert stats.success_rate is None


class TestDashboardData:
    """Tests for DashboardData model."""

    def test_dashboard_data_creation(self) -> None:
        stats = ProblemStats(
            problem_id=6,
            status="active",
            lead_count=3,
            hypothesis_count=2,
            task_count=5,
            attempt_count=10,
            success_count=1,
            last_activity=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        data = DashboardData(
            problems=[stats],
            total_attempts=10,
            total_successes=1,
            active_leads=3,
            active_hypotheses=2,
            open_tasks=5,
            attempt_timeline={"2026-01-23": ["success", "failed", "failed"]},
            generated_at=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        assert len(data.problems) == 1
        assert data.total_attempts == 10
        assert data.total_successes == 1
        assert data.overall_success_rate == 10.0

    def test_dashboard_data_overall_success_rate_no_attempts(self) -> None:
        data = DashboardData(
            problems=[],
            total_attempts=0,
            total_successes=0,
            active_leads=0,
            active_hypotheses=0,
            open_tasks=0,
            attempt_timeline={},
            generated_at=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        assert data.overall_success_rate is None

    def test_dashboard_data_to_json_snapshot(self) -> None:
        stats = ProblemStats(
            problem_id=6,
            status="active",
            lead_count=3,
            hypothesis_count=2,
            task_count=5,
            attempt_count=10,
            success_count=1,
            last_activity=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        data = DashboardData(
            problems=[stats],
            total_attempts=10,
            total_successes=1,
            active_leads=3,
            active_hypotheses=2,
            open_tasks=5,
            attempt_timeline={"2026-01-23": ["success"]},
            generated_at=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        json_data = data.to_dict()
        assert "problems" in json_data
        assert "total_attempts" in json_data
        assert "generated_at" in json_data
        assert json_data["generated_at"] == "2026-01-23T12:00:00+00:00"


class TestAggregateDashboardData:
    """Tests for aggregate_dashboard_data function."""

    def test_empty_workspace_returns_empty_dashboard(self, tmp_path: Path) -> None:
        """Dashboard works without any research workspace (empty state)."""
        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        assert len(data.problems) == 0
        assert data.total_attempts == 0
        assert data.total_successes == 0
        assert data.active_leads == 0
        assert data.active_hypotheses == 0
        assert data.open_tasks == 0

    def test_aggregates_single_problem(self, tmp_path: Path) -> None:
        """Aggregates data from a single problem workspace."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        # Add some records
        store.lead_add(6, title="Lead 1", status=LeadStatus.NEW, now=now)
        store.lead_add(6, title="Lead 2", status=LeadStatus.INVESTIGATING, now=now)
        store.hypothesis_add(
            6, statement="Hyp 1", status=HypothesisStatus.ACTIVE, now=now
        )
        store.task_add(6, title="Task 1", status=TaskStatus.TODO, now=now)
        store.task_add(6, title="Task 2", status=TaskStatus.DOING, now=now)
        store.attempt_log(
            6, result=AttemptResult.FAILED, summary="First attempt", now=now
        )
        store.attempt_log(
            6, result=AttemptResult.SUCCESS, summary="Second attempt", now=now
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert len(data.problems) == 1
        stats = data.problems[0]
        assert stats.problem_id == 6
        assert stats.lead_count == 2
        assert stats.hypothesis_count == 1
        assert stats.task_count == 2
        assert stats.attempt_count == 2
        assert stats.success_count == 1
        assert stats.success_rate == 50.0

        # Aggregate counts
        assert data.total_attempts == 2
        assert data.total_successes == 1
        assert data.active_leads == 2  # NEW and INVESTIGATING are active
        assert data.active_hypotheses == 1
        assert data.open_tasks == 2  # TODO and DOING are open

    def test_aggregates_multiple_problems(self, tmp_path: Path) -> None:
        """Aggregates data from multiple problem workspaces."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        ensure_problem_workspace(42, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        # Problem 6: 2 leads, 1 attempt
        store.lead_add(6, title="Lead A", now=now)
        store.lead_add(6, title="Lead B", now=now)
        store.attempt_log(6, result=AttemptResult.FAILED, summary="P6 attempt", now=now)

        # Problem 42: 1 lead, 2 attempts (1 success)
        store.lead_add(42, title="Lead C", now=now)
        store.attempt_log(
            42, result=AttemptResult.FAILED, summary="P42 attempt 1", now=now
        )
        store.attempt_log(
            42, result=AttemptResult.SUCCESS, summary="P42 attempt 2", now=now
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert len(data.problems) == 2
        assert data.total_attempts == 3
        assert data.total_successes == 1
        assert data.active_leads == 3

    def test_filters_by_problem_ids(self, tmp_path: Path) -> None:
        """Can filter to specific problem IDs."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        ensure_problem_workspace(42, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.lead_add(6, title="Lead A", now=now)
        store.lead_add(42, title="Lead B", now=now)

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            problem_ids=[6],
            now=now,
        )

        assert len(data.problems) == 1
        assert data.problems[0].problem_id == 6
        assert data.active_leads == 1

    def test_filters_by_recent_window(self, tmp_path: Path) -> None:
        """Filters attempts by recent time window."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)

        old_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        recent_time = datetime(2026, 1, 22, 12, 0, 0, tzinfo=UTC)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.attempt_log(
            6, result=AttemptResult.FAILED, summary="Old attempt", now=old_time
        )
        store.attempt_log(
            6, result=AttemptResult.SUCCESS, summary="Recent attempt", now=recent_time
        )

        # 7-day window should only include recent
        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            recent=timedelta(days=7),
            now=now,
        )

        assert data.total_attempts == 1
        assert data.total_successes == 1
        # Problem stats show all-time counts (1 FAILED + 1 SUCCESS = 2 attempts, 1 success)
        assert data.problems[0].attempt_count == 2
        assert data.problems[0].success_count == 1

    def test_computes_problem_status(self, tmp_path: Path) -> None:
        """Computes problem status (new/active/stale) correctly."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        ensure_problem_workspace(42, repo_root=tmp_path)
        ensure_problem_workspace(100, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)

        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)
        recent = datetime(2026, 1, 20, 12, 0, 0, tzinfo=UTC)
        old = datetime(2025, 12, 1, 12, 0, 0, tzinfo=UTC)

        # Problem 6: new (no activity)
        # Problem 42: active (recent activity)
        store.lead_add(42, title="Recent lead", now=recent)
        # Problem 100: stale (old activity)
        store.lead_add(100, title="Old lead", now=old)

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        stats_by_id = {s.problem_id: s for s in data.problems}
        assert stats_by_id[6].status == "new"
        assert stats_by_id[42].status == "active"
        assert stats_by_id[100].status == "stale"

    def test_builds_attempt_timeline(self, tmp_path: Path) -> None:
        """Builds timeline of attempts by date."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)

        day1 = datetime(2026, 1, 21, 10, 0, 0, tzinfo=UTC)
        day2 = datetime(2026, 1, 22, 14, 0, 0, tzinfo=UTC)
        day2_later = datetime(2026, 1, 22, 16, 0, 0, tzinfo=UTC)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.attempt_log(6, result=AttemptResult.FAILED, summary="Day 1", now=day1)
        store.attempt_log(
            6, result=AttemptResult.PARTIAL, summary="Day 2 morning", now=day2
        )
        store.attempt_log(
            6, result=AttemptResult.SUCCESS, summary="Day 2 afternoon", now=day2_later
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert "2026-01-21" in data.attempt_timeline
        assert data.attempt_timeline["2026-01-21"] == ["failed"]
        assert "2026-01-22" in data.attempt_timeline
        assert sorted(data.attempt_timeline["2026-01-22"]) == ["partial", "success"]

    def test_counts_active_leads_only(self, tmp_path: Path) -> None:
        """Only counts leads that are not DEAD_END or INCORPORATED."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.lead_add(6, title="Lead new", status=LeadStatus.NEW, now=now)
        store.lead_add(
            6, title="Lead investigating", status=LeadStatus.INVESTIGATING, now=now
        )
        store.lead_add(6, title="Lead promising", status=LeadStatus.PROMISING, now=now)
        store.lead_add(6, title="Lead dead_end", status=LeadStatus.DEAD_END, now=now)
        store.lead_add(
            6, title="Lead incorporated", status=LeadStatus.INCORPORATED, now=now
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        # All 5 leads in problem stats
        assert data.problems[0].lead_count == 5
        # But only 3 are "active" (NEW, INVESTIGATING, PROMISING)
        assert data.active_leads == 3

    def test_counts_active_hypotheses_only(self, tmp_path: Path) -> None:
        """Only counts hypotheses that are ACTIVE."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.hypothesis_add(
            6, statement="Hyp 1", status=HypothesisStatus.ACTIVE, now=now
        )
        store.hypothesis_add(
            6, statement="Hyp 2", status=HypothesisStatus.REFUTED, now=now
        )
        store.hypothesis_add(
            6, statement="Hyp 3", status=HypothesisStatus.PROVEN, now=now
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert data.problems[0].hypothesis_count == 3
        assert data.active_hypotheses == 1

    def test_counts_open_tasks_only(self, tmp_path: Path) -> None:
        """Only counts tasks that are TODO, DOING, or BLOCKED."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.task_add(6, title="Task 1", status=TaskStatus.TODO, now=now)
        store.task_add(6, title="Task 2", status=TaskStatus.DOING, now=now)
        store.task_add(6, title="Task 3", status=TaskStatus.BLOCKED, now=now)
        store.task_add(6, title="Task 4", status=TaskStatus.DONE, now=now)

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert data.problems[0].task_count == 4
        assert data.open_tasks == 3

    def test_determines_last_activity(self, tmp_path: Path) -> None:
        """Determines last activity from most recent record."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)

        t1 = datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 1, 21, 10, 0, 0, tzinfo=UTC)
        t3 = datetime(2026, 1, 22, 10, 0, 0, tzinfo=UTC)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.lead_add(6, title="Lead", now=t1)
        store.task_add(6, title="Task", now=t2)
        store.attempt_log(6, result=AttemptResult.FAILED, summary="Attempt", now=t3)

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        assert data.problems[0].last_activity == t3

    def test_problems_sorted_by_last_activity(self, tmp_path: Path) -> None:
        """Problems are sorted by last_activity descending (most recent first)."""
        ensure_problem_workspace(6, repo_root=tmp_path)
        ensure_problem_workspace(42, repo_root=tmp_path)
        ensure_problem_workspace(100, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)

        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.lead_add(6, title="Lead", now=datetime(2026, 1, 20, 10, 0, 0, tzinfo=UTC))
        store.lead_add(
            42, title="Lead", now=datetime(2026, 1, 22, 10, 0, 0, tzinfo=UTC)
        )
        store.lead_add(
            100, title="Lead", now=datetime(2026, 1, 21, 10, 0, 0, tzinfo=UTC)
        )

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        # Most recent first
        assert data.problems[0].problem_id == 42
        assert data.problems[1].problem_id == 100
        assert data.problems[2].problem_id == 6

    def test_generated_at_is_deterministic(self, tmp_path: Path) -> None:
        """The generated_at timestamp uses the provided now parameter."""
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)
        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )
        assert data.generated_at == now

    def test_to_dict_is_json_serializable(self, tmp_path: Path) -> None:
        """to_dict produces a JSON-serializable dict."""
        import json

        ensure_problem_workspace(6, repo_root=tmp_path)
        store = FSResearchStore(repo_root=tmp_path)
        now = datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)

        store.lead_add(6, title="Lead", now=now)
        store.attempt_log(6, result=AttemptResult.SUCCESS, summary="Test", now=now)

        data = aggregate_dashboard_data(
            research_path=tmp_path / "research",
            now=now,
        )

        # Should not raise
        json_str = json.dumps(data.to_dict())
        assert "problems" in json_str
        assert "total_attempts" in json_str
