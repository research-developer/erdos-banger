"""erdos ingest - fetch and cache reference metadata/content (SPEC-010-E, SPEC-015)."""

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
from erdos.core.batch import (
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchRunner,
    filter_problem_ids,
)
from erdos.core.constants import API_RATE_LIMIT_DELAY
from erdos.core.exit_codes import ExitCode
from erdos.core.ingest import MetadataSource, ingest_problem_references
from erdos.core.models import CLIOutput
from erdos.core.timing import measure_time_ms


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


@dataclass
class IngestOptions:
    """Options for ingest command."""

    problem_id: int | None
    force: bool = False
    no_download: bool = False
    no_network: bool = False
    timeout: float = 30.0
    delay: float = API_RATE_LIMIT_DELAY
    mailto: str = ""
    source: MetadataSource = MetadataSource.OPENALEX
    # Batch options
    all_problems: bool = False
    status: str | None = None
    prize_min: int | None = None
    prize_max: int | None = None
    tags: list[str] | None = None
    limit: int | None = None
    skip: int | None = None
    resume: bool = False
    dry_run: bool = False
    max_concurrent: int = 1
    # PDF options (SPEC-019)
    pdf: bool = False
    pdf_converter: str = "marker"
    use_llm: bool = False


app = typer.Typer(
    help="Ingest literature metadata and cache.",
    context_settings={"allow_interspersed_args": True},
)
console = Console()
err_console = Console(stderr=True)


def _print_human(result_data: dict[str, Any]) -> None:
    """Pretty-print ingestion results."""
    # Check if this is a batch result
    if "batch_id" in result_data:
        _print_human_batch(result_data)
        return

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


def _print_human_batch(result_data: dict[str, Any]) -> None:
    """Pretty-print batch ingestion results."""
    batch_id = result_data.get("batch_id", "?")
    total = result_data.get("total", 0)
    completed = result_data.get("completed", 0)
    failed = result_data.get("failed", 0)
    failed_ids = result_data.get("failed_ids", [])
    dry_run = result_data.get("dry_run", False)

    if dry_run:
        console.print(f"\n[yellow]Dry run[/yellow]: Would process {total} problems")
        problem_ids = result_data.get("problem_ids", [])
        if problem_ids:
            console.print(f"  Problem IDs: {problem_ids[:20]}")
            if len(problem_ids) > 20:
                console.print(f"  ... and {len(problem_ids) - 20} more")
        return

    if failed == 0:
        console.print(
            f"\n[bold green]✓[/bold green] Batch {batch_id} completed: "
            f"{completed}/{total} succeeded"
        )
    else:
        console.print(
            f"\n[bold yellow]![/bold yellow] Batch {batch_id} completed: "
            f"{completed}/{total} succeeded, {failed} failed"
        )
        console.print(f"  Failed IDs: {failed_ids}")


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


def _show_progress_message(problem_id: int | None, json_output: bool) -> None:
    """Show progress message if not in JSON mode."""
    if not json_output:
        if problem_id is not None:
            err_console.print(
                f"[dim]Ingesting references for Problem {problem_id}...[/dim]"
            )
        else:
            err_console.print("[dim]Starting batch ingest...[/dim]")


def _run_single_ingestion(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    *,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute single problem ingestion logic."""
    if options.problem_id is None:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="UsageError",
            message="Problem ID is required for single ingestion",
            code=ExitCode.USAGE_ERROR,
        )

    return ingest_problem_references(
        options.problem_id,
        repo=repo,
        repo_root=repo_root,
        force=options.force,
        no_download=options.no_download,
        no_network=options.no_network,
        timeout=options.timeout,
        delay=options.delay,
        mailto=mailto,
        source=options.source,
    )


def _create_batch_process_fn(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    *,
    repo: ProblemRepository,
) -> tuple[Any, Any]:
    """Create the process function for batch execution.

    Returns:
        Tuple of (process_fn, progress_callback)
    """

    def process_fn(problem_id: int) -> bool:
        """Process a single problem in batch mode."""
        result = ingest_problem_references(
            problem_id,
            repo=repo,
            repo_root=repo_root,
            force=options.force,
            no_download=options.no_download,
            no_network=options.no_network,
            timeout=options.timeout,
            delay=0.0,  # Delay handled by BatchRunner
            mailto=mailto,
            source=options.source,
        )
        return result.success

    def on_progress(progress: BatchProgress) -> None:
        """Handle progress updates."""
        status_icon = "[green]✓[/green]" if progress.success else "[red]✗[/red]"
        err_console.print(
            f"[{progress.index + 1}/{progress.total}] Problem {progress.problem_id}... "
            f"{status_icon} ({progress.message})"
        )

    return process_fn, on_progress


def _run_batch_ingestion(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    *,
    repo: ProblemRepository,
    json_mode: bool,
) -> CLIOutput:
    """Execute batch ingestion logic."""
    # Validate max_concurrent (v1.3: only 1 allowed for ingest)
    if options.max_concurrent > 1:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="UsageError",
            message="--max-concurrent > 1 is not supported for ingest (API rate limits)",
            code=ExitCode.USAGE_ERROR,
        )

    # Build filters
    filters = BatchFilters(
        status=options.status,
        prize_min=options.prize_min,
        prize_max=options.prize_max,
        tags=options.tags,
        limit=options.limit,
        skip=options.skip,
    )

    # Get problem IDs
    problems = repo.load_all()
    problem_ids = filter_problem_ids(problems, filters)

    if not problem_ids:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="NotFoundError",
            message="No problems match the given filters",
            code=ExitCode.NOT_FOUND,
        )

    # Create batch runner
    process_fn, on_progress = _create_batch_process_fn(
        options, repo_root, mailto, repo=repo
    )

    runner = BatchRunner(
        command="erdos ingest",
        problem_ids=problem_ids,
        process_fn=process_fn,
        state_dir=repo_root / "logs",
        filters=filters,
        delay=options.delay,
        on_progress=None if json_mode else on_progress,
        dry_run=options.dry_run,
        resume=options.resume,
    )

    result = runner.run()

    # Convert BatchResult to CLIOutput
    return _batch_result_to_cli_output(result, problem_ids)


def _batch_result_to_cli_output(
    result: BatchResult, problem_ids: list[int]
) -> CLIOutput:
    """Convert BatchResult to CLIOutput."""
    if result.exit_code != ExitCode.SUCCESS:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="BatchError",
            message=result.error_message,
            code=result.exit_code,
        )

    data = {
        "batch_id": result.batch_id,
        "mode": "batch",
        "total": result.total,
        "completed": result.completed_count,
        "failed": result.failed_count,
        "failed_ids": result.failed_ids,
        "dry_run": result.dry_run,
    }

    if result.dry_run:
        data["problem_ids"] = problem_ids

    if result.failed_count > 0:
        output = CLIOutput.ok(command="erdos ingest", data=data)
        output.success = False  # Mark as failure even though structure is OK
        return output

    return CLIOutput.ok(command="erdos ingest", data=data)


def _is_batch_mode(
    problem_id: int | None,
    all_problems: bool,
    status: str | None,
    prize_min: int | None,
    prize_max: int | None,
    tags: list[str] | None,
    resume: bool,
) -> bool:
    """Determine if batch mode should be activated."""
    # Batch mode if:
    # - No problem_id specified AND any batch filter is set
    # - --all is specified
    # - --resume is specified (without problem_id)
    if all_problems:
        return True
    if problem_id is None:
        return bool(
            status is not None
            or prize_min is not None
            or prize_max is not None
            or tags
            or resume
        )
    return False


@app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    problem_id: Annotated[
        int | None,
        typer.Argument(help="Problem ID (omit for batch mode)", min=1),
    ] = None,
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
    no_download: Annotated[bool, typer.Option("--no-download")] = False,
    no_network: Annotated[bool, typer.Option("--no-network")] = False,
    timeout: Annotated[float, typer.Option("--timeout")] = 30.0,
    delay: Annotated[float, typer.Option("--delay")] = API_RATE_LIMIT_DELAY,
    mailto: Annotated[str, typer.Option("--mailto")] = "",
    source: Annotated[
        MetadataSource,
        typer.Option(
            "--source",
            help="Metadata source: openalex (default), arxiv, or crossref",
            case_sensitive=False,
        ),
    ] = MetadataSource.OPENALEX,
    # Batch options
    all_problems: Annotated[
        bool,
        typer.Option("--all", help="Process all problems (batch mode)"),
    ] = False,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by status: open, proved, disproved, partially_solved, unknown",
        ),
    ] = None,
    prize_min: Annotated[
        int | None,
        typer.Option("--prize-min", help="Minimum prize amount"),
    ] = None,
    prize_max: Annotated[
        int | None,
        typer.Option("--prize-max", help="Maximum prize amount"),
    ] = None,
    tag: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by tag (can be repeated)"),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Max problems to process"),
    ] = None,
    skip: Annotated[
        int | None,
        typer.Option("--skip", help="Skip first N problems"),
    ] = None,
    resume: Annotated[
        bool,
        typer.Option("--resume", help="Resume from last incomplete batch"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be processed"),
    ] = False,
    max_concurrent: Annotated[
        int,
        typer.Option("--max-concurrent", help="Max parallel operations (ingest: 1)"),
    ] = 1,
    # PDF options (SPEC-019)
    pdf: Annotated[
        bool,
        typer.Option("--pdf", help="Enable PDF conversion for non-arXiv references"),
    ] = False,
    no_pdf: Annotated[
        bool,
        typer.Option("--no-pdf", help="Skip PDFs entirely (metadata only)"),
    ] = False,
    pdf_converter: Annotated[
        str,
        typer.Option(
            "--pdf-converter", help="PDF converter: marker (default), pdfplumber"
        ),
    ] = "marker",
    use_llm: Annotated[
        bool,
        typer.Option("--use-llm", help="Enable LLM-enhanced PDF extraction"),
    ] = False,
) -> None:
    """Ingest literature metadata and cache for problems.

    Single mode: Pass a PROBLEM_ID to ingest one problem.

    Batch mode: Omit PROBLEM_ID and use --all or filter options (--status, --prize-min,
    --prize-max, --tag) to process multiple problems. Batch state is tracked for
    resumption with --resume.

    Uses OpenAlex as the primary metadata source (271M+ works). Falls back to
    arXiv/Crossref when --source is specified.
    """
    json_mode = bool((ctx.obj or {}).get("json"))

    # Determine mode
    batch_mode = _is_batch_mode(
        problem_id, all_problems, status, prize_min, prize_max, tag, resume
    )

    # Validate: need problem_id or batch filters
    if not batch_mode and problem_id is None:
        result = CLIOutput.err(
            command="erdos ingest",
            error_type="UsageError",
            message="Provide a PROBLEM_ID or use batch options (--all, --status, --tag, etc.)",
            code=ExitCode.USAGE_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    # Prepare and execute
    _show_progress_message(problem_id if not batch_mode else None, json_mode)
    # Resolve PDF mode
    # --no-pdf takes precedence over --pdf
    pdf_enabled = pdf and not no_pdf

    options = IngestOptions(
        problem_id=problem_id,
        force=force,
        no_download=no_download,
        no_network=no_network,
        timeout=timeout,
        delay=delay,
        mailto=mailto,
        source=source,
        all_problems=all_problems,
        status=status,
        prize_min=prize_min,
        prize_max=prize_max,
        tags=tag,
        limit=limit,
        skip=skip,
        resume=resume,
        dry_run=dry_run,
        max_concurrent=max_concurrent,
        pdf=pdf_enabled,
        pdf_converter=pdf_converter,
        use_llm=use_llm,
    )
    mailto_prepared, repo_root = _prepare_ingest_options(mailto)
    app_ctx, app_error = get_app_context(ctx, command="erdos ingest")
    if app_error is not None:
        exit_with_result(ctx, app_error)
        return
    if app_ctx is None:
        return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

    with measure_time_ms() as duration:
        if batch_mode:
            result = _run_batch_ingestion(
                options,
                repo_root,
                mailto_prepared,
                repo=app_ctx.problems,
                json_mode=json_mode,
            )
        else:
            result = _run_single_ingestion(
                options, repo_root, mailto_prepared, repo=app_ctx.problems
            )

    result.duration_ms = duration[0]

    # Exit with result
    exit_with_result(ctx, result, print_human=_print_human)
