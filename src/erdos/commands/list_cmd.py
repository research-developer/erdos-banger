"""erdos list - list problems with filters."""

from __future__ import annotations

import time
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord, ProblemStatus
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


# Valid status values for user-facing validation
_VALID_STATUSES = {"open", "proved", "disproved", "partially_solved"}


app = typer.Typer(
    help="List Erdős problems with optional filters.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _print_human(problems_data: list[dict[str, Any]]) -> None:
    """Pretty-print problem list."""
    problems = [ProblemRecord.model_validate(p, strict=False) for p in problems_data]

    table = Table(title="Erdős Problems", show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Prize", justify="right")
    table.add_column("Title")

    for problem in problems:
        table.add_row(
            str(problem.id),
            problem.status.value,
            f"${problem.prize}",
            problem.title,
        )
    console.print(table)


def list_problems(
    *,
    status: str | None,
    prize_min: int | None,
    prize_max: int | None,
    tag: list[str] | None,
    limit: int,
    loader: ProblemLoader,
) -> CLIOutput:
    """Core list logic (testable)."""
    try:
        # Validate status if provided
        if status is not None:
            status_lower = status.lower()
            if status_lower not in _VALID_STATUSES:
                valid_list = ", ".join(sorted(_VALID_STATUSES))
                return CLIOutput.err(
                    command="erdos list",
                    error_type="UsageError",
                    message=f"Invalid status '{status}'. Valid values: {valid_list}",
                    code=ExitCode.USAGE_ERROR,
                )
            status_enum = ProblemStatus.from_string(status)
        else:
            status_enum = None

        problems = loader.filter(
            status=status_enum,
            prize_min=prize_min,
            prize_max=prize_max,
            tags=tag,
        )
        problems = sorted(problems, key=lambda p: p.id)[:limit]
        return CLIOutput.ok(
            command="erdos list",
            data=[p.model_dump(mode="json") for p in problems],
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos list",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


@app.callback(invoke_without_command=True)
def list_(
    ctx: typer.Context,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            "-s",
            help="Filter by status: open, proved, disproved, partially_solved",
        ),
    ] = None,
    prize_min: Annotated[
        int | None,
        typer.Option(
            "--prize-min",
            help="Minimum prize amount in USD",
            min=0,
        ),
    ] = None,
    prize_max: Annotated[
        int | None,
        typer.Option(
            "--prize-max",
            help="Maximum prize amount in USD",
            min=0,
        ),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option(
            "--tag",
            "-t",
            help="Filter by tag (can be repeated)",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of results",
            min=1,
            max=1000,
        ),
    ] = 100,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    List Erdős problems with optional filters.

    [bold]Examples:[/bold]

        # List all open problems
        erdos list --status open

        # List problems with prize >= $1000
        erdos list --prize-min 1000

        # List problems with prize <= $500
        erdos list --prize-max 500

        # List number theory problems
        erdos list --tag "number theory"

        # Combine filters
        erdos list --status open --tag primes --limit 10
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    start_time = time.perf_counter()
    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        result = CLIOutput.err(
            command="erdos list",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )
        exit_with_result(ctx, result)
        return

    result = list_problems(
        status=status,
        prize_min=prize_min,
        prize_max=prize_max,
        tag=tag,
        limit=limit,
        loader=loader,
    )
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Add duration to result
    result.duration_ms = duration_ms
    exit_with_result(ctx, result, print_human=_print_human)
