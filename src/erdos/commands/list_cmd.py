"""erdos list - list problems with filters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord, ProblemStatus
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError
from erdos.core.timing import measure_time_ms


# Valid status values for user-facing validation
_VALID_STATUSES = {"open", "proved", "disproved", "partially_solved"}


@dataclass
class ListOptions:
    """Options for the list command."""

    status: str | None
    prize_min: int | None
    prize_max: int | None
    tags: list[str] | None
    limit: int


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


def _validate_status(
    status: str | None,
) -> tuple[ProblemStatus | None, CLIOutput | None]:
    """Validate and convert status string to enum.

    Returns (status_enum, error) - error is None if valid.
    """
    if status is None:
        return None, None
    status_lower = status.lower()
    if status_lower not in _VALID_STATUSES:
        valid_list = ", ".join(sorted(_VALID_STATUSES))
        return None, CLIOutput.err(
            command="erdos list",
            error_type="UsageError",
            message=f"Invalid status '{status}'. Valid values: {valid_list}",
            code=ExitCode.USAGE_ERROR,
        )
    return ProblemStatus.from_string(status), None


def _execute_list_query(options: ListOptions, loader: ProblemLoader) -> CLIOutput:
    """Execute list query and return result."""
    status_enum, error = _validate_status(options.status)
    if error:
        return error

    try:
        problems = loader.filter(
            status=status_enum,
            prize_min=options.prize_min,
            prize_max=options.prize_max,
            tags=options.tags,
        )
        problems = sorted(problems, key=lambda p: p.id)[: options.limit]
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


def _get_loader() -> tuple[ProblemLoader | None, CLIOutput | None]:
    """Get problem loader, returning error if it fails."""
    try:
        return ProblemLoader.from_default(), None
    except ProblemLoaderError as e:
        return None, CLIOutput.err(
            command="erdos list",
            error_type="LoaderError",
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

    with measure_time_ms() as duration:
        loader, loader_error = _get_loader()
        if loader_error or loader is None:
            exit_with_result(ctx, loader_error)  # type: ignore[arg-type]
            return

        options = ListOptions(
            status=status,
            prize_min=prize_min,
            prize_max=prize_max,
            tags=tag,
            limit=limit,
        )
        result = _execute_list_query(options, loader)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
