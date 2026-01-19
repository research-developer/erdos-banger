"""erdos ingest - fetch and cache reference metadata/content (SPEC-010-E)."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.presenter import exit_with_result
from erdos.core.ingest import ingest_problem_references


app = typer.Typer(
    help="Ingest literature metadata and cache.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print ingestion results."""
    problem_id = result_data.get("problem_id", "?")
    manifest_path = result_data.get("manifest_path", "?")
    total = result_data.get("references_total", 0)
    written = result_data.get("entries_written", 0)
    skipped = result_data.get("skipped", 0)

    console.print(
        f"\n[bold green]✓[/bold green] Ingestion complete for Problem {problem_id}"
    )
    console.print(f"  Manifest: {manifest_path}")
    console.print(f"  References processed: {total}")
    console.print(f"  Entries written: {written}")
    if skipped > 0:
        console.print(f"  Skipped: {skipped}")

    # Show summary table if manifest entries exist
    manifest = result_data.get("manifest", {})
    entries = manifest.get("entries", [])
    if entries:
        table = Table(title=f"Ingested References (Problem {problem_id})")
        table.add_column("Title")
        table.add_column("Source")
        table.add_column("DOI")
        table.add_column("arXiv")

        for entry in entries[:10]:  # Show first 10
            ref = entry.get("reference", {})
            table.add_row(
                str(ref.get("title") or "")[:50],
                str(ref.get("source") or ""),
                str(ref.get("doi") or ""),
                str(ref.get("arxiv_id") or ""),
            )

        console.print(table)

        if len(entries) > 10:
            console.print(f"\n  ... and {len(entries) - 10} more entries")


def _get_repo_root() -> Path:
    """Get repository root from environment or current directory."""
    # Check for ERDOS_REPO_ROOT env var (used in tests)
    env_root = os.environ.get("ERDOS_REPO_ROOT")
    if env_root:
        return Path(env_root)

    # Default to current working directory
    return Path.cwd()


@app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Erdős problem ID to ingest references for.",
            min=1,
        ),
    ],
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Re-fetch and re-write manifest entries (even if cached).",
        ),
    ] = False,
    no_download: Annotated[
        bool,
        typer.Option(
            "--no-download",
            help="Fetch metadata only; do not download arXiv source tarballs.",
        ),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option(
            "--no-network",
            help="Fail if network access required.",
        ),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            help="HTTP timeout in seconds.",
        ),
    ] = 30.0,
    delay: Annotated[
        float,
        typer.Option(
            "--delay",
            help="Minimum delay between API requests (politeness).",
        ),
    ] = 3.0,
    mailto: Annotated[
        str,
        typer.Option(
            "--mailto",
            help="Contact email for Crossref polite pool.",
        ),
    ] = "",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON for machine consumption.",
        ),
    ] = False,
) -> None:
    """
    Ingest literature metadata and cache for a problem.

    Fetches arXiv and Crossref metadata for problem references,
    optionally downloads arXiv source tarballs, and creates/updates
    a manifest file tracking the cached literature.

    Examples:

        erdos ingest 6

        erdos ingest 6 --no-download

        erdos ingest 6 --force
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    # Get mailto from env if not provided
    if not mailto:
        mailto = os.environ.get("ERDOS_MAILTO", "erdos-banger@example.com")

    # Get repo root
    repo_root = _get_repo_root()

    start_time = time.perf_counter()

    # Show progress message (only in human mode)
    if not json_output:
        err_console.print(
            f"[dim]Ingesting references for Problem {problem_id}...[/dim]"
        )

    # Call core ingestion logic
    result = ingest_problem_references(
        problem_id,
        repo_root=repo_root,
        force=force,
        no_download=no_download,
        no_network=no_network,
        timeout=timeout,
        delay=delay,
        mailto=mailto,
    )

    # Add duration
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    # Exit with result
    exit_with_result(ctx, result, print_human=_print_human)
