"""erdos dashboard - terminal-based research dashboard (SPEC-034)."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.dashboard.data import (
    DashboardData,
    ProblemStats,
    aggregate_dashboard_data,
)
from erdos.core.dashboard.render import (
    render_dashboard,
    render_help_bar,
    render_problem_detail,
)
from erdos.core.dashboard.state import DashboardView, apply_key, initial_state
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)

app = typer.Typer(
    help="View research progress dashboard.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _parse_recent(recent: str) -> timedelta:
    """Parse --recent option value to timedelta.

    Accepts formats like: 7d, 30d, 90d, all

    Args:
        recent: String representation of time window.

    Returns:
        timedelta for the window.

    Raises:
        typer.BadParameter: If format is invalid.
    """
    if recent.lower() == "all":
        return timedelta(days=36500)  # ~100 years

    match = re.match(r"^(\d+)d$", recent.lower())
    if not match:
        raise typer.BadParameter(
            f"Invalid format '{recent}'. Expected: 7d, 30d, 90d, or 'all'"
        )
    return timedelta(days=int(match.group(1)))


def _parse_problems(problems_str: str | None) -> list[int] | None:
    """Parse --problems option value to list of IDs.

    Args:
        problems_str: Comma-separated problem IDs.

    Returns:
        List of problem IDs or None if not specified.

    Raises:
        typer.BadParameter: If format is invalid.
    """
    if not problems_str:
        return None

    ids: list[int] = []
    for raw_part in problems_str.split(","):
        part = raw_part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise typer.BadParameter(  # noqa: B904
                f"Invalid problem ID '{part}'. Expected integers."
            )
    return ids if ids else None


def _get_research_path(ctx: typer.Context) -> Path | None:
    """Get research workspace path from context."""
    app_ctx, app_error = get_app_context(ctx, command="erdos dashboard")
    if app_error is not None or app_ctx is None:
        return None
    if app_ctx.config.repo_root:
        return app_ctx.config.repo_root / "research"
    return Path.cwd() / "research"


def _aggregate_data(
    research_path: Path,
    problem_ids: list[int] | None,
    recent: timedelta,
) -> DashboardData:
    """Aggregate dashboard data."""
    return aggregate_dashboard_data(
        research_path=research_path,
        problem_ids=problem_ids,
        recent=recent,
    )


def _run_interactive(
    data: DashboardData,
    problem_id: int | None,
    research_path: Path,
    problem_ids: list[int] | None,
    recent: timedelta,
) -> None:
    """Run interactive dashboard loop.

    Args:
        data: Initial dashboard data.
        problem_id: Problem ID for detail view (or None for overview).
        research_path: Path to research workspace.
        problem_ids: Problem ID filter.
        recent: Time window filter.
    """
    state = initial_state(problem_id=problem_id)

    try:
        with Live(console=console, refresh_per_second=1, transient=True):
            while not state.should_quit:
                # Refresh data if needed
                if state.should_refresh:
                    data = _aggregate_data(research_path, problem_ids, recent)

                # Render based on current view
                console.clear()
                if state.view == DashboardView.OVERVIEW:
                    render_dashboard(console, data)
                elif state.view == DashboardView.PROBLEM_DETAIL:
                    _render_detail_view(console, data, state.selected_problem_id)
                else:
                    render_dashboard(console, data)

                # Wait for input (simplified - in a real impl would use getch)
                # For now, just break after first render in non-TTY
                if not console.is_terminal:
                    break

                try:
                    key = console.input("[dim]Press key (q=quit, r=refresh): [/dim]")
                    state = apply_key(state, key.lower())
                except (EOFError, KeyboardInterrupt):
                    break

    except Exception:
        logger.debug("Interactive mode not available", exc_info=True)


def _render_detail_view(
    con: Console,
    data: DashboardData,
    problem_id: int | None,
) -> None:
    """Render problem detail view."""
    if problem_id is None:
        render_dashboard(con, data)
        return

    # Find problem stats
    stats = next((p for p in data.problems if p.problem_id == problem_id), None)
    if stats is None:
        con.print(f"[red]Problem {problem_id} not found in research data.[/red]")
        return

    render_problem_detail(con, stats, attempts_data=[])
    render_help_bar(con, is_detail=True)


def _print_human(data: dict[str, Any]) -> None:
    """Print dashboard in human-readable format."""
    problems_data = data.get("problems", [])
    problems = [
        ProblemStats(
            problem_id=p["problem_id"],
            status=p["status"],
            lead_count=p["lead_count"],
            hypothesis_count=p["hypothesis_count"],
            task_count=p["task_count"],
            attempt_count=p["attempt_count"],
            success_count=p["success_count"],
            last_activity=None,
        )
        for p in problems_data
    ]
    dashboard_data = DashboardData(
        problems=problems,
        total_attempts=data.get("total_attempts", 0),
        total_successes=data.get("total_successes", 0),
        active_leads=data.get("active_leads", 0),
        active_hypotheses=data.get("active_hypotheses", 0),
        open_tasks=data.get("open_tasks", 0),
        attempt_timeline=data.get("attempt_timeline", {}),
        generated_at=datetime.now(UTC),
    )
    render_dashboard(console, dashboard_data)


def _parse_and_validate_options(
    ctx: typer.Context, recent: str, problems: str | None, problem: int | None
) -> tuple[timedelta, list[int] | None, Path] | CLIOutput:
    """Parse and validate dashboard options.

    Returns tuple of (recent_td, problem_ids, research_path) on success,
    or CLIOutput error on failure.
    """
    try:
        recent_td = _parse_recent(recent)
    except typer.BadParameter as e:
        return CLIOutput.err(
            command="erdos dashboard",
            error_type="UsageError",
            message=str(e),
            code=ExitCode.USAGE_ERROR,
        )

    try:
        problem_ids = _parse_problems(problems)
    except typer.BadParameter as e:
        return CLIOutput.err(
            command="erdos dashboard",
            error_type="UsageError",
            message=str(e),
            code=ExitCode.USAGE_ERROR,
        )

    if problem is not None:
        if problem_ids is None:
            problem_ids = [problem]
        elif problem not in problem_ids:
            problem_ids.append(problem)

    research_path = _get_research_path(ctx)
    if research_path is None:
        research_path = Path.cwd() / "research"

    return (recent_td, problem_ids, research_path)


@app.callback(invoke_without_command=True)
def dashboard(
    ctx: typer.Context,
    problem: int | None = typer.Option(
        None,
        "--problem",
        help="Start in detail view for a specific problem.",
    ),
    problems: str | None = typer.Option(
        None,
        "--problems",
        help="Comma-separated problem IDs to include.",
    ),
    recent: str = typer.Option(
        "30d",
        "--recent",
        help="Time window for attempts: 7d, 30d, 90d, or 'all'.",
    ),
    refresh: int = typer.Option(
        5,
        "--refresh",
        help="Enable interactive mode (non-zero) with manual 'r' to refresh. Set 0 for single-render.",
        min=0,
        max=3600,
    ),
) -> None:
    """View research progress dashboard."""
    with measure_time_ms() as duration:
        parsed = _parse_and_validate_options(ctx, recent, problems, problem)
        if isinstance(parsed, CLIOutput):
            exit_with_result(ctx, parsed)
            return
        recent_td, problem_ids, research_path = parsed

        try:
            data = _aggregate_data(research_path, problem_ids, recent_td)
        except Exception as e:
            logger.exception("Error aggregating dashboard data")
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command="erdos dashboard",
                    error_type="DashboardError",
                    message=str(e),
                    code=ExitCode.ERROR,
                ),
            )
            return

        result_data = data.to_dict()
        if problem is not None:
            problem_stats = next(
                (p for p in data.problems if p.problem_id == problem), None
            )
            if problem_stats is not None:
                result_data["problem"] = problem_stats.to_dict()
        result = CLIOutput.ok(command="erdos dashboard", data=result_data)

    result.duration_ms = duration[0]
    obj = ctx.obj
    json_mode = bool(obj.get("json", False)) if isinstance(obj, dict) else False

    if json_mode:
        exit_with_result(ctx, result)
        return

    if console.is_terminal and refresh > 0:
        _run_interactive(data, problem, research_path, problem_ids, recent_td)
    else:
        exit_with_result(ctx, result, print_human=_print_human)
