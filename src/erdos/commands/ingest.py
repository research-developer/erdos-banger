"""erdos ingest - fetch and cache reference metadata/content (SPEC-010-E)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.constants import API_RATE_LIMIT_DELAY
from erdos.core.ingest import ingest_problem_references
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


@dataclass
class IngestOptions:
    """Options for ingest command."""

    problem_id: int
    force: bool = False
    no_download: bool = False
    no_network: bool = False
    timeout: float = 30.0
    delay: float = API_RATE_LIMIT_DELAY
    mailto: str = ""


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


def _prepare_ingest_options(
    mailto: str,
) -> tuple[str, Path]:
    """Prepare ingestion options from CLI inputs.

    Returns:
        tuple: (mailto, repo_root)
    """
    # Get mailto from env if not provided
    if not mailto:
        mailto = os.environ.get("ERDOS_MAILTO", "erdos-banger@example.com")

    # Get repo root
    repo_root = _get_repo_root()

    return mailto, repo_root


def _show_progress_message(problem_id: int, json_output: bool) -> None:
    """Show progress message if not in JSON mode."""
    if not json_output:
        err_console.print(
            f"[dim]Ingesting references for Problem {problem_id}...[/dim]"
        )


def _run_ingestion(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    *,
    repo: ProblemRepository,
) -> Any:
    """Execute the core ingestion logic."""
    with measure_time_ms() as duration:
        result = ingest_problem_references(
            options.problem_id,
            repo=repo,
            repo_root=repo_root,
            force=options.force,
            no_download=options.no_download,
            no_network=options.no_network,
            timeout=options.timeout,
            delay=options.delay,
            mailto=mailto,
        )

    result.duration_ms = duration[0]
    return result


@app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    problem_id: Annotated[int, typer.Argument(help="Problem ID", min=1)],
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
    no_download: Annotated[bool, typer.Option("--no-download")] = False,
    no_network: Annotated[bool, typer.Option("--no-network")] = False,
    timeout: Annotated[float, typer.Option("--timeout")] = 30.0,
    delay: Annotated[float, typer.Option("--delay")] = API_RATE_LIMIT_DELAY,
    mailto: Annotated[str, typer.Option("--mailto")] = "",
) -> None:
    """Ingest literature metadata and cache for a problem."""
    json_mode = bool((ctx.obj or {}).get("json"))

    # Prepare and execute
    _show_progress_message(problem_id, json_mode)
    options = IngestOptions(
        problem_id, force, no_download, no_network, timeout, delay, mailto
    )
    mailto_prepared, repo_root = _prepare_ingest_options(mailto)
    app_ctx, app_error = get_app_context(ctx, command="erdos ingest")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

    result = _run_ingestion(options, repo_root, mailto_prepared, repo=app_ctx.problems)

    # Exit with result
    exit_with_result(ctx, result, print_human=_print_human)
