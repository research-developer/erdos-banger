"""Unit tests for internal helpers in erdos dashboard (SPEC-034).

These tests focus on small deterministic helpers and non-interactive branches
so we can keep coverage high without relying on real terminal I/O.
"""

from __future__ import annotations

import select
import sys
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rich.console import Console

import erdos.commands.dashboard as dashboard_cmd
from erdos.core.dashboard.data import DashboardData, ProblemStats
from erdos.core.dashboard.state import DashboardState
from erdos.core.research.models import AttemptArtifacts, AttemptRecord, AttemptResult


@contextmanager
def _fake_live(*args: object, **kwargs: object):
    """Stand-in for Rich Live context manager (no terminal side effects)."""
    yield


def _empty_dashboard_data() -> DashboardData:
    """Create an empty DashboardData instance for helper tests."""
    return DashboardData(
        problems=[],
        total_attempts=0,
        total_successes=0,
        active_leads=0,
        active_hypotheses=0,
        open_tasks=0,
        attempt_timeline={},
    )


class TestReadKey:
    """Tests for the timed input helper used by interactive mode."""

    def test_returns_none_when_stdin_missing(self, monkeypatch) -> None:
        """When sys.stdin is unavailable, _read_key returns None."""
        monkeypatch.setattr(sys, "stdin", None, raising=False)
        assert dashboard_cmd._read_key(timeout_seconds=1) is None

    def test_returns_none_when_select_errors(self, monkeypatch) -> None:
        """If select.select raises, _read_key returns None."""

        class _FakeStdin:
            def fileno(self) -> int:
                return 0

        fake_stdin = _FakeStdin()
        monkeypatch.setattr(sys, "stdin", fake_stdin, raising=False)
        monkeypatch.setattr(
            select,
            "select",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        assert dashboard_cmd._read_key(timeout_seconds=1) is None

    def test_reads_line_when_ready(self, monkeypatch) -> None:
        """When stdin is ready, _read_key reads and strips a single line."""

        class _FakeStdin:
            def fileno(self) -> int:
                return 0

            def readline(self) -> str:
                return " q \n"

        fake_stdin = _FakeStdin()
        monkeypatch.setattr(sys, "stdin", fake_stdin, raising=False)
        monkeypatch.setattr(
            select,
            "select",
            lambda *args, **kwargs: ([fake_stdin], [], []),
        )
        assert dashboard_cmd._read_key(timeout_seconds=0) == "q"


class TestInteractiveLoop:
    """Tests for non-terminal and fast-exit interactive branches."""

    def test_non_terminal_breaks_after_first_render(self, monkeypatch) -> None:
        """When not running in a real terminal, interactive loop exits quickly."""
        data = _empty_dashboard_data()

        rendered: dict[str, int] = {"count": 0}

        def _fake_render_dashboard(*args: object, **kwargs: object) -> None:
            rendered["count"] += 1

        monkeypatch.setattr(dashboard_cmd, "console", Console(force_terminal=False))
        monkeypatch.setattr(dashboard_cmd, "Live", _fake_live)
        monkeypatch.setattr(dashboard_cmd, "render_dashboard", _fake_render_dashboard)

        dashboard_cmd._run_interactive(
            data,
            None,
            Path("research"),
            None,
            timedelta(days=30),
            refresh_seconds=0,
        )
        assert rendered["count"] == 1

    def test_terminal_refresh_and_quit_path(self, monkeypatch) -> None:
        """Covers the refresh + input loop branch in a terminal context."""
        data = _empty_dashboard_data()

        aggregate_calls: dict[str, int] = {"count": 0}

        def _fake_aggregate(
            research_path: Path, problem_ids: list[int] | None, recent: timedelta
        ) -> DashboardData:
            aggregate_calls["count"] += 1
            return data

        monkeypatch.setattr(dashboard_cmd, "console", Console(force_terminal=True))
        monkeypatch.setattr(dashboard_cmd, "Live", _fake_live)
        monkeypatch.setattr(dashboard_cmd, "_aggregate_data", _fake_aggregate)
        monkeypatch.setattr(
            dashboard_cmd,
            "initial_state",
            lambda **_: DashboardState(should_refresh=True),
        )
        monkeypatch.setattr(dashboard_cmd, "_read_key", lambda **_: "q")

        # Keep the render functions as no-ops; we only care that the loop runs.
        monkeypatch.setattr(dashboard_cmd, "render_dashboard", lambda *_: None)

        dashboard_cmd._run_interactive(
            data,
            None,
            Path("research"),
            None,
            timedelta(days=30),
            refresh_seconds=5,
        )
        assert aggregate_calls["count"] == 1


class TestRenderDetailView:
    """Tests for detail view rendering helper."""

    def test_problem_id_none_renders_overview(self, monkeypatch) -> None:
        """When no problem is selected, detail view falls back to overview."""
        con = Console(force_terminal=False)
        data = _empty_dashboard_data()

        called: dict[str, bool] = {"overview": False}
        monkeypatch.setattr(
            dashboard_cmd,
            "render_dashboard",
            lambda *_: called.__setitem__("overview", True),
        )

        dashboard_cmd._render_detail_view(
            con, data, None, research_path=Path("research")
        )
        assert called["overview"] is True

    def test_missing_problem_prints_message(self) -> None:
        """When stats can't be found, an error message is printed."""
        con = Console(record=True, force_terminal=False)
        data = _empty_dashboard_data()

        dashboard_cmd._render_detail_view(
            con, data, 999, research_path=Path("research")
        )
        assert "Problem 999 not found" in con.export_text()

    def test_renders_problem_detail_with_attempts(self, monkeypatch) -> None:
        """When a problem exists, detail view renders attempt records."""
        con = Console(force_terminal=False)
        data = DashboardData(
            problems=[
                ProblemStats(
                    problem_id=6,
                    status="active",
                    lead_count=0,
                    hypothesis_count=0,
                    task_count=0,
                    attempt_count=1,
                    success_count=1,
                    last_activity=datetime.now(UTC),
                )
            ],
            total_attempts=1,
            total_successes=1,
            active_leads=0,
            active_hypotheses=0,
            open_tasks=0,
            attempt_timeline={},
        )

        attempt = AttemptRecord(
            problem_id=6,
            id="attempt-1",
            result=AttemptResult.SUCCESS,
            summary="ok",
            artifacts=AttemptArtifacts(),
            created_at=datetime.now(UTC),
        )

        class _FakeStore:
            def __init__(self, *, repo_root: Path):
                self._repo_root = repo_root

            def attempt_list(self, problem_id: int) -> list[AttemptRecord]:
                assert problem_id == 6
                return [attempt]

        captured_attempts: list[list[dict[str, object]]] = []

        def _fake_render_problem_detail(
            _console: Console,
            _stats: ProblemStats,
            *,
            attempts_data: list[dict[str, object]],
        ) -> None:
            captured_attempts.append(attempts_data)

        help_flags: list[bool] = []
        monkeypatch.setattr(dashboard_cmd, "FSResearchStore", _FakeStore)
        monkeypatch.setattr(
            dashboard_cmd, "render_problem_detail", _fake_render_problem_detail
        )
        monkeypatch.setattr(
            dashboard_cmd,
            "render_help_bar",
            lambda *_args, is_detail=False: help_flags.append(is_detail),
        )

        dashboard_cmd._render_detail_view(con, data, 6, research_path=Path("research"))

        assert captured_attempts
        assert captured_attempts[0][0]["id"] == "attempt-1"
        assert help_flags == [True]


class TestHumanRendering:
    """Tests for the human output adapter."""

    def test_print_human_parses_last_activity(self, monkeypatch) -> None:
        """_print_human should parse ISO timestamps into datetimes."""
        captured: list[DashboardData] = []
        monkeypatch.setattr(
            dashboard_cmd, "render_dashboard", lambda _c, d: captured.append(d)
        )

        dashboard_cmd._print_human(
            {
                "problems": [
                    {
                        "problem_id": 6,
                        "status": "active",
                        "lead_count": 1,
                        "hypothesis_count": 0,
                        "task_count": 0,
                        "attempt_count": 1,
                        "success_count": 1,
                        "last_activity": "2026-01-01T00:00:00Z",
                    }
                ],
                "total_attempts": 1,
                "total_successes": 1,
                "active_leads": 1,
                "active_hypotheses": 0,
                "open_tasks": 0,
                "attempt_timeline": {},
            }
        )

        assert captured
        assert captured[0].problems[0].last_activity is not None
