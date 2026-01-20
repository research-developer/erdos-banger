"""erdos refs - display references for a problem."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any, cast

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result, set_json_mode
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


app = typer.Typer(
    help="List problem references.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()


def _print_human(refs_data: dict[str, Any]) -> None:
    """Pretty-print references."""
    refs = cast("list[dict[str, Any]]", refs_data.get("references", []))

    table = Table(title=f"References for Problem {refs_data.get('problem_id')}")
    table.add_column("Key")
    table.add_column("Citation")
    table.add_column("DOI")
    table.add_column("arXiv")

    for ref in refs:
        table.add_row(
            str(ref.get("key", "")),
            str(ref.get("citation", "") or ""),
            str(ref.get("doi", "") or ""),
            str(ref.get("arxiv_id", "") or ""),
        )
    console.print(table)


def get_refs(problem_id: int, repo: ProblemRepository) -> CLIOutput:
    """Core refs logic (testable)."""
    try:
        problem = repo.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos refs",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )

        refs = [r.model_dump(mode="json") for r in problem.references]
        return CLIOutput.ok(
            command="erdos refs",
            data={"problem_id": problem_id, "references": refs},
        )
    except Exception as e:
        logger.exception("Unexpected error in refs command")
        return CLIOutput.err(
            command="erdos refs",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


@app.callback(invoke_without_command=True)
def refs(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to list references for.",
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
    List references for a problem.

    Example: erdos refs 6
    """
    set_json_mode(ctx, json_output)

    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos refs")
        if app_error is not None or app_ctx is None:
            exit_with_result(ctx, app_error)  # type: ignore[arg-type]
            return

        result = get_refs(problem_id, app_ctx.problems)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
