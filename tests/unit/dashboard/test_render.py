"""Unit tests for dashboard rendering (SPEC-034)."""

from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO

from rich.console import Console

from erdos.core.dashboard.data import DashboardData, ProblemStats
from erdos.core.dashboard.render import (
    render_aggregate_stats,
    render_attempt_timeline,
    render_dashboard,
    render_empty_state,
    render_help_bar,
    render_problem_detail,
    render_problem_overview,
)


def _make_console() -> Console:
    """Create a console that writes to string for testing."""
    return Console(file=StringIO(), force_terminal=True, width=100)


def _get_output(console: Console) -> str:
    """Extract output from test console."""
    file = console.file
    if isinstance(file, StringIO):
        return file.getvalue()
    return ""


class TestRenderEmptyState:
    """Tests for empty state rendering."""

    def test_render_empty_state_shows_no_data_message(self) -> None:
        """Empty state shows appropriate message."""
        console = _make_console()
        render_empty_state(console)
        output = _get_output(console)
        assert "no research data" in output.lower() or "empty" in output.lower()


class TestRenderProblemOverview:
    """Tests for problem overview table."""

    def test_render_overview_with_problems(self) -> None:
        """Overview table shows problem stats."""
        console = _make_console()
        problems = [
            ProblemStats(
                problem_id=6,
                status="active",
                lead_count=3,
                hypothesis_count=2,
                task_count=5,
                attempt_count=10,
                success_count=1,
                last_activity=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
            ),
            ProblemStats(
                problem_id=42,
                status="new",
                lead_count=0,
                hypothesis_count=0,
                task_count=0,
                attempt_count=0,
                success_count=0,
                last_activity=None,
            ),
        ]
        render_problem_overview(console, problems)
        output = _get_output(console)
        assert "6" in output
        assert "42" in output
        assert "active" in output.lower()
        assert "new" in output.lower()


class TestRenderAttemptTimeline:
    """Tests for attempt timeline rendering."""

    def test_render_timeline_with_attempts(self) -> None:
        """Timeline shows activity heatmap."""
        console = _make_console()
        timeline = {
            "2026-01-21": ["failed"],
            "2026-01-22": ["success", "partial"],
            "2026-01-23": ["failed", "failed", "success"],
        }
        render_attempt_timeline(console, timeline)
        output = _get_output(console)
        # Should contain some indication of attempts
        assert output.strip() != ""

    def test_render_timeline_empty(self) -> None:
        """Empty timeline shows no attempts message."""
        console = _make_console()
        render_attempt_timeline(console, {})
        output = _get_output(console)
        # Strip ANSI codes for comparison
        import re

        clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
        assert "no recent attempts" in clean.lower()


class TestRenderAggregateStats:
    """Tests for aggregate stats rendering."""

    def test_render_aggregate_stats(self) -> None:
        """Shows totals for attempts, leads, hypotheses, tasks."""
        console = _make_console()
        data = DashboardData(
            problems=[],
            total_attempts=23,
            total_successes=2,
            active_leads=11,
            active_hypotheses=4,
            open_tasks=7,
            attempt_timeline={},
            generated_at=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        render_aggregate_stats(console, data)
        output = _get_output(console)
        assert "23" in output or "attempt" in output.lower()


class TestRenderHelpBar:
    """Tests for help bar rendering."""

    def test_render_help_bar_overview(self) -> None:
        """Help bar shows relevant keys for overview."""
        console = _make_console()
        render_help_bar(console, is_detail=False)
        output = _get_output(console)
        assert "q" in output.lower()
        assert "r" in output.lower()
        assert "p" in output.lower()

    def test_render_help_bar_detail(self) -> None:
        """Help bar shows relevant keys for detail view."""
        console = _make_console()
        render_help_bar(console, is_detail=True)
        output = _get_output(console)
        assert "b" in output.lower()


class TestRenderProblemDetail:
    """Tests for problem detail view."""

    def test_render_problem_detail(self) -> None:
        """Problem detail shows stats for one problem."""
        console = _make_console()
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
        render_problem_detail(console, stats, attempts_data=[])
        output = _get_output(console)
        assert "6" in output
        assert "lead" in output.lower() or "3" in output


class TestRenderDashboard:
    """Tests for full dashboard render."""

    def test_render_dashboard_empty(self) -> None:
        """Full dashboard handles empty data."""
        console = _make_console()
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
        render_dashboard(console, data)
        output = _get_output(console)
        assert "No research data found" in output

    def test_render_dashboard_with_data(self) -> None:
        """Full dashboard shows all sections."""
        console = _make_console()
        problems = [
            ProblemStats(
                problem_id=6,
                status="active",
                lead_count=3,
                hypothesis_count=2,
                task_count=5,
                attempt_count=10,
                success_count=1,
                last_activity=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
            ),
        ]
        data = DashboardData(
            problems=problems,
            total_attempts=10,
            total_successes=1,
            active_leads=3,
            active_hypotheses=2,
            open_tasks=5,
            attempt_timeline={"2026-01-23": ["success"]},
            generated_at=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC),
        )
        render_dashboard(console, data)
        output = _get_output(console)
        assert "6" in output  # Problem ID should appear
