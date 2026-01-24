"""zbMATH subcommands for `erdos refs zbmath` (SPEC-031)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

import requests
import typer
from rich.console import Console

from erdos.commands.presenter import exit_with_result
from erdos.core.clients.zbmath import (
    MSCCode,
    ZbMathClient,
    ZbMathConfig,
    ZbMathEntry,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


app = typer.Typer(help="zbMATH Open API commands.")
console = Console()


def _get_client() -> ZbMathClient:
    """Create zbMATH client from environment config."""
    config = ZbMathConfig.from_env()
    return ZbMathClient(config)


def _format_msc_for_json(msc: MSCCode) -> dict[str, Any]:
    """Format MSC code for JSON output."""
    return {
        "code": msc.code,
        "text": msc.text,
        "primary": msc.primary,
    }


def _format_entry_for_json(entry: ZbMathEntry) -> dict[str, Any]:
    """Format entry for JSON output."""
    return {
        "zbl_id": entry.zbl_id,
        "title": entry.title,
        "authors": entry.authors,
        "year": entry.year,
        "doi": entry.doi,
        "arxiv_id": entry.arxiv_id,
        "journal": entry.journal,
        "msc": [_format_msc_for_json(m) for m in entry.msc],
        "keywords": entry.keywords,
        "review_excerpt": entry.review_excerpt,
        "zbmath_url": entry.zbmath_url,
    }


def _print_entry_human(data: dict[str, Any]) -> None:
    """Pretty-print a single entry for human consumption."""
    entry = data.get("entry", {})

    console.print(f"[bold]zbMATH Entry:[/bold] Zbl {entry.get('zbl_id', 'Unknown')}")
    console.print()

    console.print(f"[bold]Title:[/bold] {entry.get('title', 'Unknown')}")

    authors = entry.get("authors", [])
    if authors:
        console.print(f"[bold]Authors:[/bold] {'; '.join(authors)}")

    year = entry.get("year")
    if year:
        console.print(f"[bold]Year:[/bold] {year}")

    journal = entry.get("journal")
    if journal:
        console.print(f"[bold]Journal:[/bold] {journal}")

    doi = entry.get("doi")
    if doi:
        console.print(f"[bold]DOI:[/bold] {doi}")

    console.print()

    # MSC Classifications
    msc_list = entry.get("msc", [])
    if msc_list:
        console.print("[bold]MSC Classifications:[/bold]")
        for msc in msc_list:
            prefix = "  - " if not msc.get("primary") else "  - [bold]"
            suffix = "[/bold] (primary)" if msc.get("primary") else ""
            console.print(f"{prefix}{msc.get('code')}: {msc.get('text')}{suffix}")
        console.print()

    # Keywords
    keywords = entry.get("keywords", [])
    if keywords:
        console.print(f"[bold]Keywords:[/bold] {', '.join(keywords)}")
        console.print()

    # Review excerpt
    review = entry.get("review_excerpt")
    if review:
        console.print("[bold]Review (excerpt):[/bold]")
        console.print(f"  {review}")


def _print_entries_human(data: dict[str, Any]) -> None:
    """Pretty-print multiple entries for human consumption."""
    entries = data.get("entries", [])
    query = data.get("query", {})

    # Print query info
    if query.get("msc"):
        console.print(f"[bold]MSC Search:[/bold] {query['msc']}")
    if query.get("year_min") or query.get("year_max"):
        year_range = f"{query.get('year_min', '')}-{query.get('year_max', '')}"
        console.print(f"[bold]Year Range:[/bold] {year_range}")

    console.print(f"[bold]Results:[/bold] {len(entries)}")
    console.print()

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "Unknown")
        authors = "; ".join(entry.get("authors", [])[:3])  # First 3 authors
        if len(entry.get("authors", [])) > 3:
            authors += " et al."
        year = entry.get("year", "")
        year_str = f" ({year})" if year else ""
        msc_codes = ", ".join(m.get("code", "") for m in entry.get("msc", [])[:3])

        console.print(f"[bold]{i}.[/bold] {title!r}{year_str}")
        if authors:
            console.print(f"    [dim]Authors:[/dim] {authors}")
        if msc_codes:
            console.print(f"    [dim]MSC:[/dim] {msc_codes}")
        console.print()


def _lookup_entry(
    client: ZbMathClient,
    identifier: str | None,
    zbl: str | None,
    title: str | None,
) -> ZbMathEntry | None:
    """Look up a single zbMATH entry by various identifiers."""
    if zbl is not None:
        return client.get_by_zbl_id(zbl)
    if title is not None:
        entries = client.search_by_title(title, limit=1)
        return entries[0] if entries else None
    if identifier is not None:
        return client.get_by_doi(identifier)
    return None


@app.callback(invoke_without_command=True)
def zbmath(
    ctx: typer.Context,
    identifier: Annotated[
        str | None,
        typer.Argument(
            help="DOI to look up (e.g., '10.4007/annals.2008.167.481').",
        ),
    ] = None,
    zbl: Annotated[
        str | None,
        typer.Option("--zbl", help="zbMATH ID (e.g., '1191.11025')."),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option("--title", help="Title keywords to search."),
    ] = None,
    msc: Annotated[
        str | None,
        typer.Option("--msc", help="MSC code to search (e.g., '11B05')."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum results for search."),
    ] = 20,
    year_min: Annotated[
        int | None,
        typer.Option("--year-min", help="Minimum publication year."),
    ] = None,
    year_max: Annotated[
        int | None,
        typer.Option("--year-max", help="Maximum publication year."),
    ] = None,
) -> None:
    """Look up zbMATH entries or search by MSC code.

    Provides access to math-specific metadata from zbMATH Open API,
    including MSC codes, expert reviews, and math-specific keywords.

    Examples:
        erdos refs zbmath "10.4007/annals.2008.167.481"   # By DOI
        erdos refs zbmath --zbl "1191.11025"               # By zbMATH ID
        erdos refs zbmath --title "primes progressions"   # By title
        erdos refs zbmath --msc "11B05"                   # By MSC code
        erdos refs zbmath --msc "11B05" --year-min 2000   # With year filter
    """
    command = "erdos refs zbmath"

    with measure_time_ms() as duration:
        client = _get_client()

        try:
            # Determine lookup mode
            if msc is not None:
                # MSC search mode
                entries = client.search_by_msc(
                    msc,
                    limit=limit,
                    year_min=year_min,
                    year_max=year_max,
                )

                output_data: dict[str, Any] = {
                    "query": {
                        "msc": msc,
                        "limit": limit,
                        "year_min": year_min,
                        "year_max": year_max,
                    },
                    "entries": [_format_entry_for_json(e) for e in entries],
                    "returned": len(entries),
                }

                result = CLIOutput.ok(command=command, data=output_data)
                result.duration_ms = duration[0]
                exit_with_result(ctx, result, print_human=_print_entries_human)
                return

            elif zbl is not None or title is not None or identifier is not None:
                # Single-entry lookup mode
                entry = _lookup_entry(client, identifier, zbl, title)
            else:
                # No lookup specified - show help
                typer.echo(ctx.get_help())
                raise typer.Exit(code=0)

            if entry is None:
                search_term = zbl or title or identifier
                result = CLIOutput.err(
                    command=command,
                    error_type="NotFound",
                    message=f"Entry not found: {search_term}",
                    code=ExitCode.NOT_FOUND,
                )
                result.duration_ms = duration[0]
                exit_with_result(ctx, result)
                return

            output_data = {
                "identifier": zbl or title or identifier,
                "entry": _format_entry_for_json(entry),
            }

            result = CLIOutput.ok(command=command, data=output_data)

        except requests.HTTPError as e:
            result = CLIOutput.err(
                command=command,
                error_type="ZbMathError",
                message=f"zbMATH API error: {e}",
                code=ExitCode.ERROR,
            )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_entry_human)
