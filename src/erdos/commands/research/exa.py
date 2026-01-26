"""Exa Research API command for agentic literature synthesis (SPEC-029)."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

import requests
import typer

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import console, exit_with_result
from erdos.core.clients.exa import (
    DEFAULT_CACHE_PATH,
    ExaClient,
    ExaConfig,
    ExaResearchResult,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.research import FSResearchStore
from erdos.core.research.models import LeadStatus, Priority

from ._common import load_problem_or_error


app = typer.Typer(help="Exa Research API integration.")
logger = logging.getLogger(__name__)


def _exa_to_leads(
    result: ExaResearchResult,
    problem_id: int,
    store: FSResearchStore,
) -> list[str]:
    """Convert Exa sources to lead records.

    Returns list of created lead IDs.
    """
    lead_ids: list[str] = []
    for source in result.sources:
        title = (source.title or "").strip()
        if not title:
            if source.doi:
                title = f"[Exa] DOI {source.doi}"
            elif source.arxiv_id:
                title = f"[Exa] arXiv {source.arxiv_id}"
            elif source.url:
                title = f"[Exa] {source.url}"
            elif source.relevance:
                snippet = " ".join(source.relevance.split())[:80].strip()
                title = f"[Exa] {snippet}" if snippet else "[Exa] Untitled"
            else:
                title = "[Exa] Untitled"
        notes = f"[Exa] {source.relevance}" if source.relevance else "[Exa]"
        record, _ = store.lead_add(
            problem_id,
            title=title,
            doi=source.doi,
            arxiv_id=source.arxiv_id,
            url=source.url,
            status=LeadStatus.NEW,
            priority=Priority.MEDIUM,
            notes=notes,
        )
        lead_ids.append(record.id)
    return lead_ids


def _format_author_info(authors: list[str], year: int | None) -> str:
    """Format author/year citation string."""
    if not authors and not year:
        return ""
    info = ", ".join(authors[:2])
    if len(authors) > 2:
        info += " et al."
    if year:
        info += f" {year}" if info else str(year)
    return info


def _format_source_lines(index: int, src: dict[str, Any]) -> list[str]:
    """Format a single source for display."""
    parts: list[str] = []
    author_info = _format_author_info(src.get("authors", []), src.get("year"))
    title = src.get("display_title") or src.get("title") or "Untitled"

    header = f"  [bold]{index}.[/bold] {title!r}"
    if author_info:
        header = f"  [bold]{index}. [{author_info}][/bold] {title!r}"
    parts.append(header)

    # Add identifiers
    arxiv_id, doi, url = src.get("arxiv_id"), src.get("doi"), src.get("url")
    if arxiv_id:
        parts.append(f"     - arXiv: {arxiv_id}")
    if doi:
        parts.append(f"     - DOI: {doi}")
    if not arxiv_id and not doi and url:
        parts.append(f"     - URL: {url}")

    # Add relevance snippet
    relevance = src.get("relevance")
    if relevance:
        snippet = relevance[:200] + ("..." if len(relevance) > 200 else "")
        parts.append(f"     - Relevance: {snippet}")

    return parts


def _print_human_output(data: dict[str, Any]) -> None:
    """Pretty-print Exa results for human consumption."""
    console.print(f"[bold]Query:[/bold] {data['query']!r}\n")

    sources = data.get("sources", [])
    if sources:
        console.print(f"[bold]Sources ({len(sources)}):[/bold]")
        for i, src in enumerate(sources, 1):
            console.print("\n".join(_format_source_lines(i, src)))
        console.print()

    answer = data.get("answer")
    if answer:
        console.print(f"[bold]Answer:[/bold]\n  {answer}\n")

    if data.get("saved_leads"):
        lead_ids = data.get("created_lead_ids", [])
        console.print(f"[green]Created {len(lead_ids)} lead(s):[/green] {lead_ids}")

    if data.get("cached"):
        console.print("[dim](cached result)[/dim]")


def _search_with_cli_output(
    client: ExaClient,
    *,
    command: str,
    query: str,
    max_results: int,
) -> tuple[ExaResearchResult, bool] | CLIOutput:
    """Run Exa search and convert errors to a CLIOutput."""
    try:
        return client.search_with_cache_status(query, max_results=max_results)
    except json.JSONDecodeError as e:
        return CLIOutput.err(
            command=command,
            error_type="ExaError",
            message=f"Invalid JSON response from Exa API: {e}",
            code=ExitCode.ERROR,
        )
    except requests.RequestException as e:
        return CLIOutput.err(
            command=command,
            error_type="ExaError",
            message=f"Exa request error: {e}",
            code=ExitCode.ERROR,
        )
    except OSError as e:
        return CLIOutput.err(
            command=command,
            error_type="ExaError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except ValueError as e:
        return CLIOutput.err(
            command=command,
            error_type="ConfigError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )
    except Exception as e:  # final safety net for Exa integration
        logger.exception("Unexpected error in Exa search")
        return CLIOutput.err(
            command=command,
            error_type="ExaError",
            message=str(e),
            code=ExitCode.ERROR,
        )


@app.command("search")
def exa_search(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    query: Annotated[str, typer.Argument(help="Natural language research query")],
    max_results: Annotated[
        int,
        typer.Option("--max-results", help="Maximum number of sources to return"),
    ] = 5,
    save_leads: Annotated[
        bool,
        typer.Option("--save-leads", help="Auto-create lead records from results"),
    ] = False,
) -> None:
    """Search Exa Research API for relevant literature.

    Examples:
        erdos research exa search 6 "What approaches have been tried for sum-free sets?"
        erdos research exa search 42 "Progress on arithmetic progressions" --max-results 10
        erdos research exa search 124 "Graph coloring bounds" --save-leads
    """
    command = "erdos research exa"

    # Get app context
    app_ctx, app_error = get_app_context(ctx, command=command)
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return

    # Verify problem exists
    if error := load_problem_or_error(
        problem_id, repo=app_ctx.problems, command=command
    ):
        exit_with_result(ctx, error)
        return

    # Check API key
    if not app_ctx.config.exa_api_key:
        exit_with_result(
            ctx,
            CLIOutput.err(
                command=command,
                error_type="ConfigError",
                message="EXA_API_KEY not set",
                code=ExitCode.CONFIG_ERROR,
            ),
        )
        return

    # Create client and search
    config = ExaConfig(
        api_key=app_ctx.config.exa_api_key,
        cache_ttl_hours=app_ctx.config.exa_cache_ttl_hours,
        cache_path=(
            app_ctx.config.exa_cache_path
            if app_ctx.config.exa_cache_path
            else DEFAULT_CACHE_PATH
        ),
    )
    client = ExaClient(config)

    search_result = _search_with_cli_output(
        client,
        command=command,
        query=query,
        max_results=max_results,
    )

    if isinstance(search_result, CLIOutput):
        output = search_result
    else:
        result, was_cached = search_result
        cache_path = client.get_cache_path(query, max_results=max_results)

        created_lead_ids: list[str] = []
        if save_leads:
            store = FSResearchStore(repo_root=app_ctx.config.repo_root)
            created_lead_ids = _exa_to_leads(result, problem_id, store)

        output = CLIOutput.ok(
            command=command,
            data={
                "problem_id": problem_id,
                "query": query,
                "max_results": max_results,
                "sources": [s.to_dict() for s in result.sources],
                "answer": result.answer,
                "saved_leads": save_leads,
                "created_lead_ids": created_lead_ids,
                "cached": was_cached,
                "cache_path": str(cache_path),
            },
        )

    exit_with_result(
        ctx,
        output,
        print_human=_print_human_output if output.success else None,
    )
