"""erdos refs - display references for a problem."""

from __future__ import annotations

import time
from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


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


def get_refs(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    """Core refs logic (testable)."""
    try:
        problem = loader.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos refs",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=3,
            )

        refs = [r.model_dump(mode="json") for r in problem.references]
        return CLIOutput.ok(
            command="erdos refs",
            data={"problem_id": problem_id, "references": refs},
        )
    except Exception as e:
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
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    start_time = time.perf_counter()
    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        result = CLIOutput.err(
            command="erdos refs",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )
        exit_with_result(ctx, result)
        return

    result = get_refs(problem_id, loader)
    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # Add duration to result
    result.duration_ms = duration_ms
    exit_with_result(ctx, result, print_human=_print_human)
