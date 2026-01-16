"""erdos refs - display references for a problem."""

from __future__ import annotations

from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.table import Table

from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoader


app = typer.Typer(
    help="List problem references.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast("dict[str, Any]", data.data))
    else:
        error = cast("dict[str, Any]", data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


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
            code=1,
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

    loader = ProblemLoader.from_default()
    result = get_refs(problem_id, loader)
    _output(ctx, result)

    if not result.success:
        error = cast("dict[str, Any]", result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
