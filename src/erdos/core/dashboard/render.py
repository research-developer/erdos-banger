"""Dashboard Rich rendering (SPEC-034).

Rich-based terminal UI components for the dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


if TYPE_CHECKING:
    from rich.console import Console

    from erdos.core.dashboard.data import DashboardData, ProblemStats


def render_empty_state(console: Console) -> None:
    """Render empty state when no research data exists."""
    console.print(
        Panel(
            "[dim]No research data found.[/dim]\n\n"
            "Create a research workspace with:\n"
            "  [cyan]erdos research init <problem_id>[/cyan]",
            title="Dashboard",
            border_style="dim",
        )
    )


def render_problem_overview(
    console: Console,
    problems: list[ProblemStats],
) -> None:
    """Render problem overview table.

    Args:
        console: Rich console for output.
        problems: List of problem statistics.
    """
    table = Table(title="Problem Overview", show_lines=False)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Status", style="green")
    table.add_column("Leads", justify="right")
    table.add_column("Attempts", justify="right")
    table.add_column("Success", justify="right")
    table.add_column("Last Activity", style="dim")

    for p in problems:
        # Format status with color
        status_style = _status_style(p.status)
        status = Text(p.status, style=status_style)

        # Format success rate
        success_str = f"{p.success_rate:.0f}%" if p.success_rate is not None else "-"

        # Format last activity
        if p.last_activity:
            last_activity = p.last_activity.strftime("%Y-%m-%d %H:%M")
        else:
            last_activity = "-"

        table.add_row(
            str(p.problem_id),
            status,
            str(p.lead_count),
            str(p.attempt_count),
            success_str,
            last_activity,
        )

    console.print(table)


def _status_style(status: str) -> str:
    """Return Rich style for problem status."""
    styles = {
        "active": "green",
        "new": "blue",
        "stale": "yellow",
    }
    return styles.get(status, "white")


def render_attempt_timeline(
    console: Console,
    timeline: dict[str, list[str]],
) -> None:
    """Render attempt activity heatmap.

    Args:
        console: Rich console for output.
        timeline: Date -> list of result values.
    """
    if not timeline:
        console.print("[dim]No recent attempts.[/dim]")
        return

    # Sort dates and build visual representation
    sorted_dates = sorted(timeline.keys())

    # Build heatmap line
    heatmap_chars = []
    for date in sorted_dates:
        results = timeline[date]
        for result in results:
            char = _result_char(result)
            heatmap_chars.append(char)

    heatmap = "".join(heatmap_chars)

    console.print("\n[bold]Recent Attempts[/bold]")
    console.print(f"  {heatmap}")
    console.print(
        "  [dim]Legend: [green]●[/green]=success [red]●[/red]=failed "
        "[yellow]●[/yellow]=partial[/dim]"
    )


def _result_char(result: str) -> str:
    """Return colored character for attempt result."""
    chars = {
        "success": "[green]●[/green]",
        "failed": "[red]●[/red]",
        "partial": "[yellow]●[/yellow]",
    }
    return chars.get(result, "[dim]○[/dim]")


def render_aggregate_stats(console: Console, data: DashboardData) -> None:
    """Render aggregate statistics.

    Args:
        console: Rich console for output.
        data: Dashboard data with aggregate counts.
    """
    console.print("\n[bold]Aggregate Stats[/bold]")

    # Success rate
    if data.overall_success_rate is not None:
        success_str = (
            f"{data.overall_success_rate:.1f}% "
            f"({data.total_successes}/{data.total_attempts})"
        )
    else:
        success_str = "-"

    stats_lines = [
        f"  Total attempts: {data.total_attempts}",
        f"  Success rate: {success_str}",
        f"  Active leads: {data.active_leads}",
        f"  Active hypotheses: {data.active_hypotheses}",
        f"  Open tasks: {data.open_tasks}",
    ]
    console.print("\n".join(stats_lines))


def render_help_bar(console: Console, *, is_detail: bool = False) -> None:
    """Render keyboard help bar at bottom.

    Args:
        console: Rich console for output.
        is_detail: True if showing detail view help.
    """
    if is_detail:
        help_text = "[q] Quit  [r] Refresh  [b] Back  [a] Attempt detail"
    else:
        help_text = "[q] Quit  [r] Refresh  [p] Problem detail"

    console.print(f"\n[dim]{help_text}[/dim]")


def render_problem_detail(
    console: Console,
    stats: ProblemStats,
    attempts_data: list[dict[str, object]],
) -> None:
    """Render problem detail view.

    Args:
        console: Rich console for output.
        stats: Statistics for the problem.
        attempts_data: List of attempt records (dicts with id, result, summary).
    """
    # Header
    console.print(
        Panel(
            f"[bold]Problem {stats.problem_id}[/bold]",
            border_style=_status_style(stats.status),
        )
    )

    # Stats table
    table = Table(show_header=False, box=None)
    table.add_column("Label", style="dim")
    table.add_column("Value")

    table.add_row("Status", Text(stats.status, style=_status_style(stats.status)))
    table.add_row("Leads", str(stats.lead_count))
    table.add_row("Hypotheses", str(stats.hypothesis_count))
    table.add_row("Tasks", str(stats.task_count))
    table.add_row("Attempts", str(stats.attempt_count))
    if stats.success_rate is not None:
        table.add_row("Success Rate", f"{stats.success_rate:.1f}%")

    console.print(table)

    # Recent attempts
    if attempts_data:
        console.print("\n[bold]Recent Attempts[/bold]")
        for attempt in attempts_data[:5]:  # Show last 5
            result = str(attempt.get("result", "unknown"))
            summary = str(attempt.get("summary", ""))[:50]
            result_style = {
                "success": "green",
                "failed": "red",
                "partial": "yellow",
            }.get(result, "white")
            console.print(f"  [{result_style}]{result}[/{result_style}]: {summary}")


def render_dashboard(console: Console, data: DashboardData) -> None:
    """Render the full dashboard view.

    Args:
        console: Rich console for output.
        data: Aggregated dashboard data.
    """
    # Header
    console.print(
        Panel(
            f"[bold]ERDOS-BANGER DASHBOARD[/bold]\n"
            f"[dim]Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M')}[/dim]",
            border_style="blue",
        )
    )

    if not data.problems:
        render_empty_state(console)
        return

    # Problem overview
    render_problem_overview(console, data.problems)

    # Attempt timeline
    render_attempt_timeline(console, data.attempt_timeline)

    # Aggregate stats
    render_aggregate_stats(console, data)

    # Help bar
    render_help_bar(console)
