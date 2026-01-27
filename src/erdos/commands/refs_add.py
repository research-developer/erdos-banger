"""`erdos refs add` - add reference identifiers to a problem dataset.

This command intentionally updates the **local** enriched dataset file (e.g.
`data/problems_enriched.yaml`) so that subsequent `erdos ingest <id>` runs can
discover and ingest the newly-added references.
"""

from __future__ import annotations

import logging
from typing import Annotated

import typer
from pydantic import ValidationError

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ReferenceEntry
from erdos.core.refs import add_reference_to_problem
from erdos.core.sync.dataset import (
    resolve_enriched_dataset_path,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


def _build_reference_entry(
    *,
    command: str,
    arxiv_id: str | None,
    doi: str | None,
    url: str | None,
    key: str | None,
    citation: str | None,
) -> tuple[ReferenceEntry | None, CLIOutput | None]:
    normalized_arxiv = arxiv_id.strip() if arxiv_id else None
    normalized_doi = doi.strip().lower() if doi else None
    normalized_url = url.strip() if url else None
    normalized_key = key.strip() if key else None
    normalized_citation = citation.strip() if citation else None

    identifiers = [v for v in (normalized_arxiv, normalized_doi, normalized_url) if v]
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

    derived_url = normalized_url
    if derived_url is None and normalized_arxiv:
        derived_url = f"https://arxiv.org/abs/{normalized_arxiv}"
    if derived_url is None and normalized_doi:
        derived_url = f"https://doi.org/{normalized_doi}"

    derived_key = normalized_key
    if derived_key is None:
        if normalized_arxiv:
            derived_key = f"arXiv:{normalized_arxiv}"
        elif normalized_doi:
            derived_key = f"DOI:{normalized_doi}"
        else:
            derived_key = "URL"

    try:
        reference = ReferenceEntry(
            key=derived_key,
            citation=normalized_citation,
            doi=normalized_doi,
            arxiv_id=normalized_arxiv,
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
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command=command,
                    error_type="UnexpectedError",
                    message=f"Unexpected missing app context for command {command}",
                    code=ExitCode.ERROR,
                ),
            )
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
