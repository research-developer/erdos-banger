"""erdos refs - display references for a problem."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any, cast

import click
import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms

from . import refs_s2, refs_zbmath


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


class RefsGroup(TyperGroup):
    """Custom TyperGroup that handles backward-compat `erdos refs <id>` syntax.

    When a numeric argument is passed that would be interpreted as an unknown command,
    redirects to the 'problem' subcommand for backward compatibility with the original
    `erdos refs <problem_id>` syntax.
    """

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """Override to handle numeric 'commands' as problem IDs."""
        if args and args[0].isdigit():
            # Numeric argument - redirect to "problem" subcommand
            return "problem", self.get_command(ctx, "problem"), args
        return super().resolve_command(ctx, args)


app = typer.Typer(
    help="List problem references, query Semantic Scholar, or look up zbMATH.",
    cls=RefsGroup,
)

# Register subcommands FIRST (before the default command)
app.add_typer(refs_s2.app, name="s2")
app.add_typer(refs_zbmath.app, name="zbmath")
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


@app.command("problem")
def refs_problem(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to list references for.",
            min=1,
        ),
    ],
) -> None:
    """
    List references for a problem.

    Example: erdos refs problem 6
    """
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos refs")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

        result = get_refs(problem_id, app_ctx.problems)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


@app.callback(invoke_without_command=True)
def refs_callback(ctx: typer.Context) -> None:
    """
    List problem references, query Semantic Scholar, or look up zbMATH.

    Examples:
        erdos refs 6
        erdos refs problem 6
        erdos refs s2 citations "10.4007/annals.2008.167.481"
        erdos refs s2 cited-by "math/0404188"
        erdos refs zbmath "10.4007/annals.2008.167.481"
        erdos refs zbmath --msc "11B05"
    """
    # If a subcommand was invoked, let it handle things
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand invoked - show help
    console.print(ctx.get_help())
    raise typer.Exit(code=ExitCode.SUCCESS)
