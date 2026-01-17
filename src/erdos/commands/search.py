"""erdos search - search problem statements."""

from __future__ import annotations

from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.table import Table

from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.problem_loader import ProblemLoader, ProblemLoaderError


app = typer.Typer(
    help="Search problem statements.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast("list[dict[str, Any]]", data.data))
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human(results_data: list[dict[str, Any]]) -> None:
    """Pretty-print search results."""
    problems = [ProblemRecord.model_validate(p, strict=False) for p in results_data]

    table = Table(title="Search Results")
    table.add_column("ID", justify="right")
    table.add_column("Title")
    table.add_column("Status")

    for problem in problems:
        table.add_row(str(problem.id), problem.title, problem.status.value)
    console.print(table)


def search_problems(query: str, loader: ProblemLoader) -> CLIOutput:
    """Core search logic (testable)."""
    try:
        q = query.lower().strip()
        if not q:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=2,
            )

        matches: list[ProblemRecord] = []
        for problem in loader.load_all():
            if q in problem.title.lower() or q in problem.statement.lower():
                matches.append(problem)

        matches = sorted(matches, key=lambda p: p.id)
        return CLIOutput.ok(
            command="erdos search",
            data=[p.model_dump(mode="json") for p in matches],
        )
    except Exception as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=1,
        )


@app.callback(invoke_without_command=True)
def search(
    ctx: typer.Context,
    query: Annotated[
        str,
        typer.Argument(
            help="Search query text.",
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
    Search problem statements for a query.

    Example: erdos search "prime"
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        result = CLIOutput.err(
            command="erdos search",
            error_type="LoaderError",
            message=str(e),
            code=1,
        )
        _output(ctx, result)
        raise typer.Exit(code=1) from None

    result = search_problems(query, loader)
    _output(ctx, result)

    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
