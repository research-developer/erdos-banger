"""erdos sync proof - extract proof links from forum threads (SPEC-035)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.sync.forum import (
    ForumFetchError,
    fetch_and_parse_forum,
    parse_forum_html,
    save_proof_links_cache,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)
console = Console()


# =============================================================================
# Data paths
# =============================================================================

DEFAULT_CACHE_PATH = Path("data/sync_cache/proofs")


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    DEFAULT_CACHE_PATH.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Core logic
# =============================================================================


def sync_proof_links(
    problem_id: int,
    *,
    dry_run: bool = False,
    html_content: str | None = None,
) -> CLIOutput:
    """
    Sync proof links from a forum thread.

    This is the core logic, separated from CLI concerns for testing.

    Args:
        problem_id: Problem ID to sync
        dry_run: If True, don't write to disk
        html_content: Pre-fetched HTML (for testing with fixtures)

    Returns:
        CLIOutput with sync result
    """
    cached = html_content is not None

    try:
        # Either parse from provided HTML or fetch from network
        if html_content is not None:
            cache = parse_forum_html(html_content, problem_id)
        else:
            cache = fetch_and_parse_forum(problem_id)

        # Save the links cache
        if not dry_run:
            _ensure_cache_dir()
            provenance_path = save_proof_links_cache(
                cache, cache_dir=DEFAULT_CACHE_PATH
            )
        else:
            provenance_path = DEFAULT_CACHE_PATH / str(problem_id) / "links.json"

        return CLIOutput.ok(
            command="erdos sync proof",
            data={
                "problem_id": problem_id,
                "links": [
                    {
                        "url": link.url,
                        "author": link.author,
                        "lean_version_hint": link.lean_version_hint,
                    }
                    for link in cache.links
                ],
                "links_count": len(cache.links),
                "provenance_path": str(provenance_path),
                "cached": cached,
                "verification_status": "unverified",  # Task 5/5 will implement --verify
            },
        )

    except ForumFetchError as e:
        code = ExitCode.NETWORK_ERROR if e.status_code != 404 else ExitCode.NOT_FOUND
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="FetchError",
            message=str(e),
            code=code,
        )
    except Exception as e:
        logger.exception("Unexpected error in sync proof")
        return CLIOutput.err(
            command="erdos sync proof",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


# =============================================================================
# Human output
# =============================================================================


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print sync result for humans."""
    problem_id = data.get("problem_id", "?")
    links = data.get("links", [])
    links_count = data.get("links_count", 0)
    cached = data.get("cached", False)
    provenance_path = data.get("provenance_path", "")
    verification_status = data.get("verification_status", "unverified")

    source_text = "(from cache)" if cached else "(from network)"

    if links_count == 0:
        content = f"No proof repository links found {source_text}"
        panel = Panel(
            content,
            title=f"Problem #{problem_id} - Proof Links",
            expand=False,
        )
        console.print(panel)
        return

    # Create a table of links
    table = Table(show_header=True, header_style="bold")
    table.add_column("URL", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Lean Version", style="yellow")

    for link in links:
        table.add_row(
            link.get("url", "?"),
            link.get("author") or "-",
            link.get("lean_version_hint") or "-",
        )

    lines = [
        f"[bold]Problem #{problem_id}[/bold] {source_text}",
        f"Found {links_count} proof link(s)",
        f"Verification: {verification_status}",
        f"Saved to: {provenance_path}",
    ]

    panel = Panel(
        "\n".join(lines),
        title="\u2713 Proof Links Extracted",
        expand=False,
    )
    console.print(panel)
    console.print(table)


# =============================================================================
# CLI Command
# =============================================================================


def proof(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to extract proof links for",
            min=1,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be extracted without writing to disk",
        ),
    ] = False,
) -> None:
    """
    Extract proof repository links from the forum thread.

    Fetches the forum thread for the given problem and extracts GitHub/GitLab
    repository links. Writes the results to data/sync_cache/proofs/<id>/links.json.

    This command only extracts and records links. Use --verify (in a future
    version) to also clone and verify the proofs.

    Example:
        erdos sync proof 347
        erdos sync proof 347 --dry-run
    """
    with measure_time_ms() as duration:
        result = sync_proof_links(
            problem_id,
            dry_run=dry_run,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
