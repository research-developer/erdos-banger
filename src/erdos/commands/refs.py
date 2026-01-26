"""erdos refs - display references for a problem."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any, cast

import click
import typer
from pydantic import ValidationError
from rich.table import Table
from typer.core import TyperGroup

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import console, exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ReferenceEntry
from erdos.core.sync.dataset import (
    load_enriched_problems,
    resolve_enriched_dataset_path,
    save_enriched_problems,
)
from erdos.core.timing import measure_time_ms

from . import refs_s2, refs_zbmath


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.models import ProblemRecord
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
                error_type="NotFoundError",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )

        refs = [r.model_dump(mode="json") for r in problem.references]
        return CLIOutput.ok(
            command="erdos refs",
            data={"problem_id": problem_id, "references": refs},
        )
    except Exception as e:  # final safety net; convert unexpected failures to CLIOutput
        logger.exception("Unexpected error in refs command")
        return CLIOutput.err(
            command="erdos refs",
            error_type="UnexpectedError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _dedupe_key(key: str, existing_keys: set[str]) -> str:
    if key not in existing_keys:
        return key
    suffix = 2
    while f"{key}-{suffix}" in existing_keys:
        suffix += 1
    return f"{key}-{suffix}"


def _normalize_identifier(value: str) -> str:
    return value.strip()


def _normalize_doi(value: str) -> str:
    return value.strip().lower()


def _build_reference_entry(
    *,
    command: str,
    arxiv_id: str | None,
    doi: str | None,
    url: str | None,
    key: str | None,
    citation: str | None,
) -> tuple[ReferenceEntry | None, CLIOutput | None]:
    identifiers = [v for v in (arxiv_id, doi, url) if v]
    if not identifiers:
        return (
            None,
            CLIOutput.err(
                command=command,
                error_type="UsageError",
                message="Must provide at least one of: --arxiv/--arxiv-id, --doi, --url",
                code=ExitCode.USAGE_ERROR,
            ),
        )

    derived_url = url
    if derived_url is None and arxiv_id:
        derived_url = f"https://arxiv.org/abs/{arxiv_id.strip()}"
    if derived_url is None and doi:
        derived_url = f"https://doi.org/{doi.strip()}"

    derived_key = key
    if derived_key is None:
        if arxiv_id:
            derived_key = f"arXiv:{arxiv_id.strip()}"
        elif doi:
            derived_key = f"DOI:{doi.strip()}"
        else:
            derived_key = "URL"

    try:
        reference = ReferenceEntry(
            key=derived_key,
            citation=citation,
            doi=doi,
            arxiv_id=arxiv_id,
            url=derived_url,
        )
    except (ValidationError, ValueError) as e:
        return (
            None,
            CLIOutput.err(
                command=command,
                error_type="UsageError",
                message=str(e),
                code=ExitCode.USAGE_ERROR,
            ),
        )

    return reference, None


def add_reference_to_problem(
    *,
    problem_id: int,
    reference: ReferenceEntry,
    dataset_path: Path,
) -> tuple[ProblemRecord | None, bool, ReferenceEntry | None, str | None]:
    """Add a ReferenceEntry to the local enriched dataset.

    Returns:
        (updated_problem, updated, stored_reference, error_message)
    """
    try:
        problems = load_enriched_problems(dataset_path)
        problem = problems.get(problem_id)
        if problem is None:
            return None, False, None, f"Problem {problem_id} not found in dataset"

        existing_keys = {r.key for r in problem.references}
        existing_dois: dict[str, ReferenceEntry] = {}
        existing_arxiv: dict[str, ReferenceEntry] = {}
        for ref in problem.references:
            if ref.doi is not None:
                existing_dois[_normalize_doi(ref.doi)] = ref
            if ref.arxiv_id is not None:
                existing_arxiv[_normalize_identifier(ref.arxiv_id)] = ref

        doi = _normalize_doi(reference.doi) if reference.doi else None
        arxiv_id = (
            _normalize_identifier(reference.arxiv_id) if reference.arxiv_id else None
        )

        if doi is not None and doi in existing_dois:
            return problem, False, existing_dois[doi], None
        if arxiv_id is not None and arxiv_id in existing_arxiv:
            return problem, False, existing_arxiv[arxiv_id], None

        key = _dedupe_key(reference.key, existing_keys)
        ref = (
            reference
            if key == reference.key
            else reference.model_copy(update={"key": key})
        )

        updated_refs = [*problem.references, ref]
        updated_problem = problem.model_copy(update={"references": updated_refs})
        problems[problem_id] = updated_problem
        save_enriched_problems(dataset_path, problems)
        return updated_problem, True, ref, None
    except Exception as e:
        logger.exception("Failed to update dataset references")
        return None, False, None, str(e)


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


@app.command("add")
def refs_add(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID to update.", min=1)],
    arxiv_id: Annotated[
        str | None,
        typer.Option(
            "--arxiv",
            "--arxiv-id",
            help="Add an arXiv ID to the problem references (e.g., 2511.16072).",
        ),
    ] = None,
    doi: Annotated[
        str | None, typer.Option("--doi", help="Add a DOI to the references.")
    ] = None,
    url: Annotated[
        str | None, typer.Option("--url", help="Add a URL to the references.")
    ] = None,
    key: Annotated[
        str | None,
        typer.Option(
            "--key",
            help="Reference key to store in the dataset (default derived from identifier).",
        ),
    ] = None,
    citation: Annotated[
        str | None,
        typer.Option("--citation", help="Citation text to store in the dataset."),
    ] = None,
) -> None:
    """Add a reference identifier to a problem in the local dataset.

    This updates the local enriched dataset file (e.g. `data/problems_enriched.yaml`),
    so subsequent `erdos ingest <id>` runs can fetch metadata and ingest content.

    Examples:
        erdos refs add 848 --arxiv 2511.16072
        erdos refs add 848 --doi 10.1000/example
        erdos refs add 848 --url https://example.com/paper.pdf --key Example2026
    """
    command = "erdos refs add"
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command=command)
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return

        dataset_path = resolve_enriched_dataset_path(app_ctx.config)

        reference, reference_error = _build_reference_entry(
            command=command,
            arxiv_id=arxiv_id,
            doi=doi,
            url=url,
            key=key,
            citation=citation,
        )
        if reference_error is not None:
            exit_with_result(ctx, reference_error)
            return
        if reference is None:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command=command,
                    error_type="UnexpectedError",
                    message="Invariant violation: reference is None but reference_error is None",
                    code=ExitCode.ERROR,
                ),
            )
            return

        updated_problem, updated, stored_ref, err = add_reference_to_problem(
            problem_id=problem_id,
            reference=reference,
            dataset_path=dataset_path,
        )
        if err is not None:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command=command,
                    error_type="IOError",
                    message=err,
                    code=ExitCode.ERROR,
                ),
            )
            return
        if updated_problem is None:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command=command,
                    error_type="NotFoundError",
                    message=f"Problem {problem_id} not found",
                    code=ExitCode.NOT_FOUND,
                ),
            )
            return

        if stored_ref is None:
            stored_ref = reference

        result = CLIOutput.ok(
            command=command,
            data={
                "problem_id": problem_id,
                "dataset_path": str(dataset_path),
                "updated": updated,
                "reference": stored_ref.model_dump(mode="json"),
                "references_total": len(updated_problem.references),
            },
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result)


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
