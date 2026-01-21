"""erdos show - display problem details."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


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
def get_problem(problem_id: int, repo: ProblemRepository) -> CLIOutput:
    """
    Get a problem by ID.

    This is the core logic, separated from CLI concerns for testing.
    """
    try:
        problem = repo.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos show",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )
        return CLIOutput.ok(
            command="erdos show",
            data=problem.model_dump(mode="json"),
        )
    except Exception as e:
        logger.exception("Unexpected error in show command")
        return CLIOutput.err(
            command="erdos show",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
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
) -> None:
    """
    Show detailed information about an Erdős problem.

    Example: erdos show 6
    """

    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos show")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

        result = get_problem(problem_id, app_ctx.problems)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
