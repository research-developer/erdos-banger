"""Lead commands for `erdos research` (Spec 024, SPEC-030, SPEC-031)."""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.clients.semantic_scholar import S2Config, SemanticScholarClient
from erdos.core.clients.zbmath import ZbMathClient, ZbMathConfig
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import LeadStatus, Priority

from ._common import handle_store_error, load_problem_or_error


logger = logging.getLogger(__name__)
app = typer.Typer(help="Manage leads.")


def _fetch_s2_citation_intent(identifier: str | None) -> str | None:
    """Fetch citation intent from Semantic Scholar if identifier available.

    Args:
        identifier: DOI or arXiv ID to look up.

    Returns:
        Citation intent string to append to notes, or None if lookup fails.
    """
    if not identifier:
        return None

    try:
        config = S2Config.from_env()
        client = SemanticScholarClient(config)
        paper = client.get_paper(identifier)
        if paper is None:
            logger.debug("S2 paper not found: %s", identifier)
            return None

        # Get a sample of citations to understand how paper is cited
        citations = client.get_citations(paper.s2_id, limit=5)
        if not citations:
            return None

        # Aggregate intents
        all_intents: list[str] = []
        for c in citations:
            all_intents.extend(c.intents)

        if not all_intents:
            return None

        # Count intents
        intent_counts: dict[str, int] = {}
        for intent in all_intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # Format as annotation
        intent_summary = ", ".join(
            f"{k}:{v}" for k, v in sorted(intent_counts.items(), key=lambda x: -x[1])
        )
        return f"[S2 intents: {intent_summary}]"

    except Exception as e:  # best-effort external metadata lookup
        logger.debug("S2 citation fetch failed: %s", e)
        return None


def _fetch_zbmath_msc(identifier: str | None) -> list[str] | None:
    """Fetch MSC codes from zbMATH if DOI available.

    Args:
        identifier: DOI to look up.

    Returns:
        List of MSC codes, or None if lookup fails.
    """
    if not identifier or not identifier.startswith("10."):
        return None

    try:
        config = ZbMathConfig.from_env()
        client = ZbMathClient(config)
        entry = client.get_by_doi(identifier)
        if entry is None:
            logger.debug("zbMATH entry not found: %s", identifier)
            return None

        msc_codes = [m.code for m in entry.msc]
        return msc_codes if msc_codes else None

    except Exception as e:  # best-effort external metadata lookup
        logger.debug("zbMATH MSC fetch failed: %s", e)
        return None


@app.command("add")
def lead_add(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    title: Annotated[str, typer.Option("--title", help="Lead title")],
    doi: Annotated[str | None, typer.Option("--doi")] = None,
    arxiv_id: Annotated[str | None, typer.Option("--arxiv-id")] = None,
    url: Annotated[str | None, typer.Option("--url")] = None,
    status: Annotated[LeadStatus, typer.Option("--status")] = LeadStatus.NEW,
    priority: Annotated[Priority, typer.Option("--priority")] = Priority.MEDIUM,
    notes: Annotated[str, typer.Option("--notes")] = "",
    fetch_citations: Annotated[
        bool,
        typer.Option(
            "--fetch-citations",
            help="Fetch citation intent from Semantic Scholar (SPEC-030).",
        ),
    ] = False,
    fetch_msc: Annotated[
        bool,
        typer.Option(
            "--fetch-msc",
            help="Fetch MSC codes from zbMATH (SPEC-031). Requires DOI.",
        ),
    ] = False,
) -> None:
    """Add a lead record.

    Optionally enrich with metadata from external APIs:
    - --fetch-citations: Add Semantic Scholar citation intent to notes
    - --fetch-msc: Add zbMATH MSC codes as tags (requires DOI)
    """
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead add")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead add"
    ):
        exit_with_result(ctx, error)
        return

    # Enrich notes with Semantic Scholar citation intent
    enriched_notes = notes
    s2_enrichment: str | None = None
    if fetch_citations:
        identifier = doi or arxiv_id
        s2_enrichment = _fetch_s2_citation_intent(identifier)
        if s2_enrichment:
            enriched_notes = (
                f"{notes} {s2_enrichment}".strip() if notes else s2_enrichment
            )

    # Fetch MSC codes from zbMATH
    msc_codes: list[str] | None = None
    if fetch_msc:
        msc_codes = _fetch_zbmath_msc(doi)

    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.lead_add(
            problem_id,
            title=title,
            doi=doi,
            arxiv_id=arxiv_id,
            url=url,
            status=status,
            priority=priority,
            notes=enriched_notes,
            tags=msc_codes,
        )
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research lead add", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead add",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
                "s2_enrichment": s2_enrichment,
                "msc_codes": msc_codes,
            },
        ),
    )


@app.command("list")
def lead_list(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    status: Annotated[LeadStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
) -> None:
    """List lead records."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead list")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead list"
    ):
        exit_with_result(ctx, error)
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        records = store.lead_list(problem_id, status=status, priority=priority)
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research lead list", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead list",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "records": [r.model_dump(mode="json") for r in records],
            },
        ),
    )


@app.command("update")
def lead_update(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    lead_id: Annotated[str, typer.Argument(help="Lead ID (filename stem)")],
    status: Annotated[LeadStatus | None, typer.Option("--status")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Update a lead record."""
    app_ctx, app_error = get_app_context(ctx, command="erdos research lead update")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command="erdos research lead update"
    ):
        exit_with_result(ctx, error)
        return
    if status is None and priority is None and notes is None:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command="erdos research lead update",
                error_type="UsageError",
                message="At least one of --status, --priority, or --notes is required",
                code=ExitCode.USAGE_ERROR,
            ),
        )
        return
    store = FSResearchStore(repo_root=app_ctx.config.repo_root)
    try:
        record, path = store.lead_update(
            problem_id, lead_id, status=status, priority=priority, notes=notes
        )
    except Exception as e:  # map store failures to CLIOutput
        exit_with_result(ctx, handle_store_error("erdos research lead update", e))
        return

    exit_with_result(
        ctx,
        CLIOutput.ok(
            command="erdos research lead update",
            data={
                "problem_id": problem_id,
                "record_kind": "lead",
                "path": str(path.resolve()),
                "record": record.model_dump(mode="json"),
            },
        ),
    )
