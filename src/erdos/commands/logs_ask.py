"""erdos logs ask - query `erdos ask` interaction logs."""

from __future__ import annotations

import logging
from typing import Any

import typer
from rich.table import Table

from erdos.commands.presenter import console, exit_with_result
from erdos.core.ask.logging import AskLogEntry, read_ask_log_entries
from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import CLIOutput
from erdos.core.run_logger import parse_since
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


app = typer.Typer(
    help="Query `erdos ask` interaction logs (logs/ask/*.jsonl).",
    context_settings={"allow_interspersed_args": True},
)


def _entry_to_dict(entry: AskLogEntry) -> dict[str, Any]:
    return entry.model_dump(mode="json")


def query_ask_logs(
    *,
    problem_id: int,
    limit: int = 50,
    since: str | None = None,
) -> CLIOutput:
    """Core logic: query ask logs for a single problem."""
    try:
        since_dt = parse_since(since) if since else None
        entries, parse_errors, log_path = read_ask_log_entries(
            problem_id,
            limit=limit,
            since=since_dt,
        )
        return CLIOutput.ok(
            command="erdos logs ask",
            data={
                "problem_id": problem_id,
                "log_path": str(log_path),
                "parse_errors": parse_errors,
                "entries": [_entry_to_dict(e) for e in entries],
            },
        )
    except ValueError as e:
        return CLIOutput.err(
            command="erdos logs ask",
            error_type="UsageError",
            message=str(e),
            code=2,
        )
    except Exception as e:  # final safety net; log querying should never crash CLI
        logger.exception("Error querying ask logs")
        return CLIOutput.err(
            command="erdos logs ask",
            error_type="UnexpectedError",
            message=str(e),
            code=1,
        )


def _print_entries_human(data: dict[str, Any]) -> None:
    entries = data.get("entries", [])
    if not entries:
        console.print("[dim]No ask log entries found.[/dim]")
        return

    table = Table(title=f"Ask Logs (Problem {data.get('problem_id', '?')})")
    table.add_column("Timestamp", style="cyan", no_wrap=True)
    table.add_column("Question", style="green")
    table.add_column("Answer", style="white")
    table.add_column("Sources", justify="right")
    table.add_column("LLM", justify="center")

    for entry in entries:
        timestamp = str(entry.get("timestamp") or "")
        if "T" in timestamp:
            timestamp = timestamp.replace("T", " ")[:19]

        question = str(entry.get("question") or "")
        if len(question) > PREVIEW_LENGTH:
            question = question[:PREVIEW_LENGTH] + "…"

        answer = entry.get("answer")
        answer_text = "" if answer is None else str(answer)
        if len(answer_text) > PREVIEW_LENGTH:
            answer_text = answer_text[:PREVIEW_LENGTH] + "…"

        sources = str(entry.get("source_count") or 0)
        llm = entry.get("llm", {})
        llm_enabled = bool(llm.get("enabled"))
        llm_indicator = "✓" if llm_enabled else "-"

        table.add_row(timestamp, question, answer_text, sources, llm_indicator)

    console.print(table)

    parse_errors = int(data.get("parse_errors", 0) or 0)
    if parse_errors:
        console.print(f"[dim]Skipped {parse_errors} malformed log lines.[/dim]")


@app.callback(invoke_without_command=True)
def ask_logs(
    ctx: typer.Context,
    problem_id: int = typer.Option(
        ...,
        "--problem",
        "--problem-id",
        "-p",
        help="Problem ID to query.",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Max entries to return.",
        min=1,
        max=1000,
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Filter logs after date (e.g., '7d', '2h', '2026-01-15').",
    ),
) -> None:
    """Query ask logs for a problem.

    Examples:
        erdos logs ask --problem 848 --limit 5
        erdos logs ask --problem 6 --since 7d
    """
    with measure_time_ms() as duration:
        result = query_ask_logs(problem_id=problem_id, limit=limit, since=since)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_entries_human)
