"""Ingest application service: pure orchestration for batch and single-problem ingest.

This module provides the application-layer orchestration for the ingest command,
separating business logic from CLI concerns (Typer/Rich). All functions here:
- Accept typed options dataclasses
- Return CLIOutput or domain results
- Have no dependencies on Typer, Rich, or console output
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from erdos.core.batch import (
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchRunner,
    filter_problem_ids,
)
from erdos.core.config import AppConfig
from erdos.core.constants import API_RATE_LIMIT_DELAY, DEFAULT_HTTP_TIMEOUT
from erdos.core.exit_codes import ExitCode
from erdos.core.ingest.fetch import MetadataSource
from erdos.core.ingest.service import ingest_problem_references
from erdos.core.models import CLIOutput
from erdos.core.repo_root import discover_repo_root


if TYPE_CHECKING:
    from collections.abc import Callable

    from erdos.core.ports import ProblemRepository


@dataclass
class IngestOptions:
    """Options for ingest command - pure data, no CLI dependencies."""

    problem_id: int | None
    force: bool = False
    no_download: bool = False
    no_network: bool = False
    timeout: float | None = None
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


def get_repo_root(*, repo_root: Path | None = None) -> Path:
    """Get repository root.

    Args:
        repo_root: Explicit path (falls back to ERDOS_REPO_ROOT, then cwd).

    Returns:
        Repository root path.
    """
    if repo_root is not None:
        return repo_root.resolve()
    config_repo_root = AppConfig.from_env().repo_root
    if config_repo_root is not None:
        return config_repo_root.resolve()
    return discover_repo_root() or Path.cwd().resolve()


def prepare_mailto(mailto: str, *, default: str | None = None) -> str:
    """Prepare mailto from CLI input, config default, or environment.

    Precedence:
        1) Explicit CLI value (non-empty)
        2) default (if provided and non-empty)
        3) ERDOS_MAILTO environment variable
        4) Stable fallback "erdos-banger@example.com" for local dev
    """
    if mailto.strip():
        return mailto.strip()
    if default is not None and default.strip():
        return default.strip()
    return AppConfig.from_env().mailto


def is_batch_mode(options: IngestOptions) -> bool:
    """Determine if batch mode should be activated based on options.

    Batch mode is activated if:
    - --all is specified
    - No problem_id AND any batch filter is set (status, prize, tags, resume)
    """
    if options.all_problems:
        return True
    if options.problem_id is None:
        return bool(
            options.status is not None
            or options.prize_min is not None
            or options.prize_max is not None
            or options.tags
            or options.resume
        )
    return False


def run_single_ingestion(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    timeout: float,
    openalex_api_key: str | None,
    *,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute single problem ingestion.

    Args:
        options: Ingest options.
        repo_root: Repository root path.
        mailto: Contact email for API polite pools.
        repo: Problem repository.

    Returns:
        CLIOutput with ingestion results.
    """
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
        timeout=timeout,
        delay=options.delay,
        mailto=mailto,
        pdf=options.pdf,
        pdf_converter=options.pdf_converter,
        pdf_use_llm=options.use_llm,
        source=options.source,
        openalex_api_key=openalex_api_key,
    )


def batch_result_to_cli_output(
    result: BatchResult, problem_ids: list[int]
) -> CLIOutput:
    """Convert BatchResult to CLIOutput.

    Args:
        result: Batch execution result.
        problem_ids: Original list of problem IDs (for dry run output).

    Returns:
        CLIOutput with batch results.
    """
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
        # Partial failure: use CLIOutput.err with batch data in error dict
        return CLIOutput.err(
            command="erdos ingest",
            error_type="PartialBatchFailure",
            message=f"{result.failed_count} of {result.total} problems failed",
            code=ExitCode.ERROR,
        )

    return CLIOutput.ok(command="erdos ingest", data=data)


def create_batch_process_fn(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    timeout: float,
    openalex_api_key: str | None,
    *,
    repo: ProblemRepository,
) -> Callable[[int], bool]:
    """Create the process function for batch execution.

    Args:
        options: Ingest options.
        repo_root: Repository root path.
        mailto: Contact email for API polite pools.
        repo: Problem repository.

    Returns:
        Function that processes a single problem ID and returns True on success.
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
            timeout=timeout,
            delay=0.0,  # Delay handled by BatchRunner
            mailto=mailto,
            pdf=options.pdf,
            pdf_converter=options.pdf_converter,
            pdf_use_llm=options.use_llm,
            source=options.source,
            openalex_api_key=openalex_api_key,
        )
        return result.success

    return process_fn


def run_batch_ingestion(
    options: IngestOptions,
    repo_root: Path,
    mailto: str,
    timeout: float,
    openalex_api_key: str | None,
    *,
    repo: ProblemRepository,
    on_progress: Callable[[BatchProgress], None] | None = None,
) -> CLIOutput:
    """Execute batch ingestion.

    Args:
        options: Ingest options.
        repo_root: Repository root path.
        mailto: Contact email for API polite pools.
        repo: Problem repository.
        on_progress: Optional progress callback (set to None for JSON mode).

    Returns:
        CLIOutput with batch results.
    """
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
    process_fn = create_batch_process_fn(
        options,
        repo_root,
        mailto,
        timeout,
        openalex_api_key,
        repo=repo,
    )

    runner = BatchRunner(
        command="erdos ingest",
        problem_ids=problem_ids,
        process_fn=process_fn,
        state_dir=repo_root / "logs",
        filters=filters,
        delay=options.delay,
        on_progress=on_progress,
        dry_run=options.dry_run,
        resume=options.resume,
    )

    result = runner.run()

    return batch_result_to_cli_output(result, problem_ids)


def execute_ingest(
    options: IngestOptions,
    *,
    repo: ProblemRepository,
    on_progress: Callable[[BatchProgress], None] | None = None,
    repo_root: Path | None = None,
    mailto_default: str | None = None,
    timeout_default: float | None = None,
    openalex_api_key: str | None = None,
) -> CLIOutput:
    """Main ingest orchestration: determines mode and executes.

    This is the primary entrypoint for ingest operations, called by the CLI.

    Args:
        options: Complete ingest options.
        repo: Problem repository.
        on_progress: Optional progress callback for batch mode (set to None for JSON mode).

    Returns:
        CLIOutput with results.
    """
    # Determine mode
    batch_mode = is_batch_mode(options)

    # Validate: need problem_id or batch filters
    if not batch_mode and options.problem_id is None:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="UsageError",
            message="Provide a PROBLEM_ID or use batch options (--all, --status, --tag, etc.)",
            code=ExitCode.USAGE_ERROR,
        )

    # Prepare common options
    mailto = prepare_mailto(options.mailto, default=mailto_default)
    resolved_timeout = (
        options.timeout
        if options.timeout is not None
        else (timeout_default if timeout_default is not None else DEFAULT_HTTP_TIMEOUT)
    )
    resolved_repo_root = get_repo_root(repo_root=repo_root)

    # Execute
    if batch_mode:
        return run_batch_ingestion(
            options,
            resolved_repo_root,
            mailto,
            resolved_timeout,
            openalex_api_key,
            repo=repo,
            on_progress=on_progress,
        )
    else:
        return run_single_ingestion(
            options,
            resolved_repo_root,
            mailto,
            resolved_timeout,
            openalex_api_key,
            repo=repo,
        )
