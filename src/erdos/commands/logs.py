"""erdos logs - query and summarize run logs."""

from __future__ import annotations

import logging
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.models import CLIOutput
from erdos.core.run_logger import RunLogEntry, RunLogger, get_run_logger
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


app = typer.Typer(
    help="Query and summarize run logs.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _entry_to_dict(entry: RunLogEntry) -> dict[str, Any]:
    """Convert a log entry to dict for JSON output."""
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "command": entry.command,
        "args": entry.args,
        "duration_ms": entry.duration_ms,
        "success": entry.success,
        "problem_id": entry.problem_id,
        "result": entry.result,
        "error": entry.error,
    }


def _print_entries_human(data: dict[str, Any]) -> None:
    """Pretty-print log entries for humans."""
    entries = data.get("entries", [])
    if not entries:
        console.print("[dim]No log entries found.[/dim]")
        return

    table = Table(title="Run Logs", show_lines=True)
    table.add_column("Timestamp", style="cyan", no_wrap=True)
    table.add_column("Command", style="green")
    table.add_column("Problem", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Status")

    for entry in entries:
        timestamp = entry.get("timestamp", "")
        if "T" in timestamp:
            # Shorten timestamp for display
            timestamp = timestamp.replace("T", " ")[:19]

        command = entry.get("command", "")
        problem_id = str(entry.get("problem_id") or "-")
        duration = entry.get("duration_ms")
        duration_str = f"{duration}ms" if duration else "-"

        success = entry.get("success", True)
        status = "[green]✓[/green]" if success else "[red]✗[/red]"

        table.add_row(timestamp, command, problem_id, duration_str, status)

    console.print(table)


def _print_summary_human(data: dict[str, Any]) -> None:
    """Pretty-print log summary for humans."""
    console.print(f"\n[bold]Summary[/bold] ({data.get('total_runs', 0)} total runs)\n")

    # Period
    period = data.get("period", {})
    if period.get("from"):
        console.print(f"[dim]Period:[/dim] {period.get('from')} → {period.get('to')}\n")

    # By command
    by_command = data.get("by_command", {})
    if by_command:
        table = Table(title="By Command", show_lines=False)
        table.add_column("Command", style="green")
        table.add_column("Runs", justify="right")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Failure", justify="right", style="red")

        for cmd, stats in sorted(by_command.items()):
            table.add_row(
                cmd,
                str(stats.get("runs", 0)),
                str(stats.get("success", 0)),
                str(stats.get("failure", 0)),
            )
        console.print(table)

    # By problem
    by_problem = data.get("by_problem", {})
    if by_problem:
        console.print()
        table = Table(title="By Problem", show_lines=False)
        table.add_column("Problem ID", justify="right")
        table.add_column("Runs", justify="right")
        table.add_column("Last Success", style="dim")

        for pid, stats in sorted(by_problem.items(), key=lambda x: int(x[0])):
            last_success = stats.get("last_success") or "-"
            if last_success != "-" and "T" in last_success:
                last_success = last_success.replace("T", " ")[:19]
            table.add_row(pid, str(stats.get("runs", 0)), last_success)
        console.print(table)

    # Metrics
    metrics = data.get("metrics", {})
    if metrics:
        console.print("\n[bold]Metrics[/bold]")
        console.print(f"  Problems attempted: {metrics.get('problems_attempted', 0)}")
        console.print(
            f"  Lean compiles passed: {metrics.get('lean_compiles_passed', 0)}"
        )
        console.print(
            f"  Lean compiles failed: {metrics.get('lean_compiles_failed', 0)}"
        )


# ============================================================================
# Core Logic (testable independently)
# ============================================================================


def query_logs(
    run_logger: RunLogger,
    *,
    problem_id: int | None = None,
    command: str | None = None,
    since: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> CLIOutput:
    """Query log entries with filters.

    Args:
        run_logger: RunLogger instance
        problem_id: Filter by problem ID
        command: Filter by command name
        since: Filter by timestamp
        status: Filter by success/failure
        limit: Max entries to return

    Returns:
        CLIOutput with entries list
    """
    try:
        entries = run_logger.query(
            problem_id=problem_id,
            command=command,
            since=since,
            status=status,
            limit=limit,
        )
        return CLIOutput.ok(
            command="erdos logs",
            data={"entries": [_entry_to_dict(e) for e in entries]},
        )
    except ValueError as e:
        return CLIOutput.err(
            command="erdos logs",
            error_type="UsageError",
            message=str(e),
            code=2,
        )
    except Exception as e:
        logger.exception("Error querying logs")
        return CLIOutput.err(
            command="erdos logs",
            error_type="Error",
            message=str(e),
            code=1,
        )


def summarize_logs(
    run_logger: RunLogger,
    *,
    problem_id: int | None = None,
    command: str | None = None,
    since: str | None = None,
) -> CLIOutput:
    """Get aggregated summary of log entries.

    Args:
        run_logger: RunLogger instance
        problem_id: Filter by problem ID
        command: Filter by command name
        since: Filter by timestamp

    Returns:
        CLIOutput with summary data
    """
    try:
        summary = run_logger.summary(
            problem_id=problem_id,
            command=command,
            since=since,
        )
        return CLIOutput.ok(command="erdos logs", data=summary)
    except ValueError as e:
        return CLIOutput.err(
            command="erdos logs",
            error_type="UsageError",
            message=str(e),
            code=2,
        )
    except Exception as e:
        logger.exception("Error computing log summary")
        return CLIOutput.err(
            command="erdos logs",
            error_type="Error",
            message=str(e),
            code=1,
        )


# ============================================================================
# CLI Command
# ============================================================================


@app.callback(invoke_without_command=True)
def logs(
    ctx: typer.Context,
    problem_id: int | None = typer.Option(
        None,
        "--problem-id",
        "-p",
        help="Filter by problem ID.",
    ),
    command: str | None = typer.Option(
        None,
        "--command",
        help="Filter by command name (e.g., 'erdos lean check').",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Filter logs after date (e.g., '7d', '2h', '2026-01-15').",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by 'success' or 'failure'.",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Max entries to return.",
        min=1,
        max=1000,
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="Show aggregated summary instead of individual entries.",
    ),
) -> None:
    """
    Query and summarize run logs.

    Examples:
        erdos logs --limit 10
        erdos logs --problem-id 6 --command "erdos lean check"
        erdos logs --since 7d --summary
    """
    with measure_time_ms() as duration:
        run_logger = get_run_logger()

        if summary:
            result = summarize_logs(
                run_logger,
                problem_id=problem_id,
                command=command,
                since=since,
            )
            print_human = _print_summary_human
        else:
            result = query_logs(
                run_logger,
                problem_id=problem_id,
                command=command,
                since=since,
                status=status,
                limit=limit,
            )
            print_human = _print_entries_human

    result.duration_ms = duration[0]
    # Note: logs command itself is not logged to avoid infinite recursion
    exit_with_result(ctx, result, print_human=print_human)
