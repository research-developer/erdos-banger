"""erdos show - display problem details."""

from __future__ import annotations

import time
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel

from erdos.commands.presenter import exit_with_result
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


app = typer.Typer(
    help="Show detailed problem information.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _print_human(problem_data: dict[str, Any]) -> None:
    """Pretty-print problem for humans."""
    problem = ProblemRecord.model_validate(problem_data, strict=False)

    title = f"[bold]Problem {problem.id}:[/bold] {problem.title}"
    status_color = {
        "open": "yellow",
        "proved": "green",
        "disproved": "red",
    }.get(problem.status.value, "white")

    panel = Panel(
        f"""
[bold]Status:[/bold] [{status_color}]{problem.status.value}[/{status_color}]
[bold]Prize:[/bold] ${problem.prize}
[bold]Tags:[/bold] {", ".join(problem.tags) or "None"}

[bold]Statement:[/bold]
{problem.statement}
        """.strip(),
        title=title,
        expand=False,
    )
    console.print(panel)


# ============================================================================
# Core Logic (testable independently)
# ============================================================================


def get_problem(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    """
    Get a problem by ID.

    This is the core logic, separated from CLI concerns for testing.
    """
    try:
        problem = loader.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos show",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=3,
            )
        return CLIOutput.ok(
            command="erdos show",
            data=problem.model_dump(mode="json"),
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos show",
            error_type="Error",
            message=str(e),
            code=1,
        )


# ============================================================================
# CLI Command
# ============================================================================


@app.callback(invoke_without_command=True)
def show(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to display.",
            min=1,
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Show detailed information about an Erdős problem.

    Example: erdos show 6
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    start_time = time.perf_counter()
    try:
        loader = ProblemLoader.from_default()  # Uses configured data path
    except ProblemLoaderError as e:
        result = CLIOutput.err(
            command="erdos show",
            error_type="LoaderError",
            message=str(e),
            code=1,
        )
        exit_with_result(ctx, result)
        return

    result = get_problem(problem_id, loader)
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Add duration to result
    result.duration_ms = duration_ms
    exit_with_result(ctx, result, print_human=_print_human)
