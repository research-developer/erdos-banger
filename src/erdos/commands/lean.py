"""erdos lean - Lean 4 integration commands (SPEC-007, SPEC-015)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

from erdos.commands.app_context import get_app_context
from erdos.commands.presenter import exit_with_result
from erdos.core.aristotle import AristotleError, run_aristotle_prove_from_file
from erdos.core.batch import (
    BatchFilters,
    BatchProgress,
    BatchResult,
    filter_problem_ids,
    generate_batch_id,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.formal_conjectures import (
    FORMAL_CONJECTURES_REPO,
    FormalConjecturesError,
    LocalFormalizationInfo,
    ProvenanceEntry,
    build_upstream_url,
    fetch_upstream_lean_file,
    get_cache_path,
    get_local_file_path,
    load_provenance,
    load_upstream_metadata,
    save_provenance,
)
from erdos.core.formalizer import FormalizerError, generate_skeleton
from erdos.core.lean_runner import LeanRunner, LeanRunnerError
from erdos.core.models import CLIOutput, LeanCheckResult
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)

# Default upstream metadata path
UPSTREAM_METADATA_PATH = Path("data/erdosproblems/data/problems.yaml")


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


app = typer.Typer(help="Lean 4 theorem prover commands.")
console = Console()


def _print_human_check_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Lean check result."""
    result = LeanCheckResult.model_validate(result_data, strict=False)

    if result.success:
        console.print(f"[green]✓[/green] {result.file} compiled successfully")
    else:
        console.print(f"[red]✗[/red] {result.file} has {result.error_count} error(s)")
        for error in result.errors:
            console.print(f"  {error}")


def _print_human_formalize_result(result_data: dict[str, Any]) -> None:
    """Pretty-print formalize result."""
    output_file = result_data["file"]
    console.print(f"[green]✓[/green] Created {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def _print_human_prove_result(result_data: dict[str, Any]) -> None:
    """Pretty-print Aristotle prove result."""
    output_file = result_data["output_file"]
    console.print(f"[green]✓[/green] Proof generated at {output_file}")
    console.print(f"  Run: erdos lean check {output_file}")


def _print_human_status_result(result_data: dict[str, Any]) -> None:
    """Pretty-print lean status result."""
    if "summary" in result_data:
        # All problems summary
        summary = result_data["summary"]
        total = summary.get("total", 0)
        upstream_formalized = summary.get("upstream_formalized", 0)
        local_exists = summary.get("local_exists", 0)
        console.print(f"Formalization Status ({total} problems)")
        console.print()
        console.print(f"  Upstream formalized: {upstream_formalized}")
        console.print(f"  Local files exist:   {local_exists}")
    else:
        # Single problem
        problem_id = result_data.get("problem_id", "?")
        console.print(f"Problem {problem_id}")
        console.print()

        # Upstream info
        upstream = result_data.get("upstream", {})
        if upstream.get("available"):
            state = "formalized" if upstream.get("formalized") else "not formalized"
            console.print(f"Upstream: {state}")
            if upstream.get("url"):
                console.print(f"  URL: {upstream['url']}")
        else:
            console.print("Upstream: [dim]no metadata available[/dim]")

        # Local info
        local = result_data.get("local", {})
        if local.get("exists"):
            sorry_str = "yes" if local.get("has_sorry") else "no"
            console.print(f"Local: {local.get('path')}")
            console.print(f"  Has sorry: {sorry_str}")
        else:
            console.print("Local: [dim]no file[/dim]")

        # Comparison
        comparison = result_data.get("comparison")
        if comparison:
            console.print(f"Comparison: {comparison}")


def _print_human_import_result(result_data: dict[str, Any]) -> None:
    """Pretty-print lean import result."""
    path = result_data.get("path")
    dry_run = result_data.get("dry_run", False)
    written = result_data.get("written", False)

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] Would import to {path}")
    elif written:
        console.print(f"[green]✓[/green] Imported to {path}")
        validated = result_data.get("lean_validated", False)
        if validated:
            console.print("  Lean validation: passed")
        else:
            console.print("  [yellow]Lean validation: skipped[/yellow]")
    else:
        console.print(f"[yellow]![/yellow] File already up to date: {path}")


def _print_human(result_data: Any) -> None:
    if isinstance(result_data, dict):
        # LeanCheckResult has "file" and "success" keys
        if {"file", "success"}.issubset(result_data.keys()):
            _print_human_check_result(result_data)
        # Formalize result has "problem_id" and "file" keys (but not "upstream"/"local")
        elif (
            {"problem_id", "file"}.issubset(result_data.keys())
            and "upstream" not in result_data
            and "local" not in result_data
            and "dry_run" not in result_data
        ):
            _print_human_formalize_result(result_data)
        # Aristotle prove result has "input_file", "output_file", "aristotle" keys
        elif {"input_file", "output_file", "aristotle"}.issubset(result_data.keys()):
            _print_human_prove_result(result_data)
        # Init result has "project_path" and "initialized" keys
        elif {"project_path", "initialized"}.issubset(result_data.keys()):
            console.print(
                f"[green]✓[/green] Initialized Lean project at {result_data['project_path']}"
            )
        # Status result has "upstream" or "local" or "summary" keys
        elif (
            "upstream" in result_data
            or "local" in result_data
            or "summary" in result_data
        ):
            _print_human_status_result(result_data)
        # Import result has "dry_run" and "written" keys
        elif "dry_run" in result_data and "written" in result_data:
            _print_human_import_result(result_data)
        else:
            console.print(result_data)
    else:
        console.print(result_data)


# ============================================================================
# Core Logic
# ============================================================================


def init_lean_project(project_path: Path, *, fetch_mathlib: bool = True) -> CLIOutput:
    """Initialize Lean project structure."""
    try:
        runner = LeanRunner(project_path)
        runner.init(fetch_mathlib=fetch_mathlib)
        return CLIOutput.ok(
            command="erdos lean init",
            data={"project_path": str(project_path), "initialized": True},
        )
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean init command")
        return CLIOutput.err(
            command="erdos lean init",
            error_type="InitError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def check_lean_file(file_path: Path, project_path: Path) -> CLIOutput:
    """Check a Lean file for errors."""
    try:
        runner = LeanRunner(project_path)
        result = runner.check(file_path)
        return CLIOutput.ok(
            command="erdos lean check",
            data=result.model_dump(mode="json"),
        )
    except LeanRunnerError as e:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="LeanRunnerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except FileNotFoundError:
        return CLIOutput.err(
            command="erdos lean check",
            error_type="NotFound",
            message=f"File not found: {file_path}",
            code=ExitCode.NOT_FOUND,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean check command")
        return CLIOutput.err(
            command="erdos lean check",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def formalize_problem(
    problem_id: int,
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
) -> CLIOutput:
    """Generate a Lean skeleton for a problem."""
    try:
        problem = repo.get_by_id(problem_id)
        if problem is None:
            return CLIOutput.err(
                command="erdos lean formalize",
                error_type="NotFound",
                message=f"Problem {problem_id} not found",
                code=ExitCode.NOT_FOUND,
            )

        output_file = generate_skeleton(problem, project_path, overwrite=force)
        return CLIOutput.ok(
            command="erdos lean formalize",
            data={"problem_id": problem_id, "file": str(output_file)},
        )
    except FormalizerError as e:
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="FormalizerError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean formalize command")
        return CLIOutput.err(
            command="erdos lean formalize",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _get_comparison(upstream_formalized: bool, local_exists: bool) -> str:
    """Get comparison string between upstream and local status."""
    if upstream_formalized and local_exists:
        return "both_exist"
    if upstream_formalized:
        return "upstream_only"
    if local_exists:
        return "local_only"
    return "neither"


def _get_upstream_data(
    problem_id: int,
    upstream_info: dict[int, Any],
    check_upstream: bool,
) -> dict[str, Any]:
    """Build upstream data dict for status response."""
    if not check_upstream or problem_id not in upstream_info:
        return {"available": False}
    info = upstream_info[problem_id]
    return {
        "available": True,
        "formalized": info.formalized,
        "state": info.state,
        "last_update": info.last_update,
        "source": FORMAL_CONJECTURES_REPO,
        "url": build_upstream_url(problem_id) if info.formalized else None,
    }


def _get_local_data(
    project_path: Path, problem_id: int, check_local: bool
) -> dict[str, Any]:
    """Build local data dict for status response."""
    if not check_local:
        return {"exists": False}
    local_path = get_local_file_path(project_path, problem_id)
    local_info = LocalFormalizationInfo.from_file(local_path)
    if not local_info.exists:
        return {"exists": False}
    return {
        "exists": True,
        "path": str(local_path),
        "has_sorry": local_info.has_sorry,
        "sha256": local_info.sha256,
    }


def get_formalization_status(
    problem_id: int | None,
    project_path: Path,
    *,
    repo: ProblemRepository,
    check_upstream: bool = True,
    check_local: bool = True,
) -> CLIOutput:
    """Get formalization status for a problem or all problems."""
    try:
        upstream_info: dict[int, Any] = {}
        if check_upstream:
            if not UPSTREAM_METADATA_PATH.exists():
                return CLIOutput.err(
                    command="erdos lean status",
                    error_type="ConfigError",
                    message=f"Upstream metadata not found: {UPSTREAM_METADATA_PATH}. "
                    "Run 'git submodule update --init --recursive' to fetch.",
                    code=ExitCode.CONFIG_ERROR,
                )
            upstream_info = load_upstream_metadata(UPSTREAM_METADATA_PATH)

        if problem_id is not None:
            return _get_single_problem_status(
                problem_id,
                project_path,
                repo,
                upstream_info,
                check_upstream,
                check_local,
            )
        return _get_all_problems_status(project_path, repo, upstream_info)
    except FormalConjecturesError as e:
        return CLIOutput.err(
            command="erdos lean status",
            error_type=e.error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean status command")
        return CLIOutput.err(
            command="erdos lean status",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def _get_single_problem_status(
    problem_id: int,
    project_path: Path,
    repo: ProblemRepository,
    upstream_info: dict[int, Any],
    check_upstream: bool,
    check_local: bool,
) -> CLIOutput:
    """Get status for a single problem."""
    problem = repo.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(
            command="erdos lean status",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    upstream_data = _get_upstream_data(problem_id, upstream_info, check_upstream)
    local_data = _get_local_data(project_path, problem_id, check_local)
    comparison = _get_comparison(
        upstream_data.get("formalized", False), local_data.get("exists", False)
    )

    return CLIOutput.ok(
        command="erdos lean status",
        data={
            "problem_id": problem_id,
            "upstream": upstream_data,
            "local": local_data,
            "comparison": comparison,
        },
    )


def _get_all_problems_status(
    project_path: Path,
    repo: ProblemRepository,
    upstream_info: dict[int, Any],
) -> CLIOutput:
    """Get summary status for all problems."""
    problems = repo.load_all()
    total = len(problems)
    upstream_formalized = sum(
        1
        for p in problems
        if upstream_info.get(p.id, None) and upstream_info[p.id].formalized
    )
    local_exists = sum(
        1 for p in problems if get_local_file_path(project_path, p.id).exists()
    )

    return CLIOutput.ok(
        command="erdos lean status",
        data={
            "summary": {
                "total": total,
                "upstream_formalized": upstream_formalized,
                "local_exists": local_exists,
            }
        },
    )


def _validate_imported_file(
    project_path: Path, local_path: Path, skip_validation: bool
) -> bool | CLIOutput:
    """Validate imported file with Lean. Returns bool or CLIOutput on error."""
    if skip_validation:
        return False
    try:
        runner = LeanRunner(project_path)
        check_result = runner.check(local_path)
        if not check_result.success:
            return CLIOutput.err(
                command="erdos lean import",
                error_type="LeanError",
                message=f"Imported file has Lean errors: {check_result.errors}",
                code=ExitCode.LEAN_ERROR,
            )
        return True
    except LeanRunnerError as e:
        logger.warning("Lean validation failed: %s", e)
        return False


def _update_provenance(
    local_path: Path,
    problem_id: int,
    fetch_result: Any,
) -> None:
    """Update provenance file after import."""
    prov_path = local_path.parent / ".provenance.yaml"
    prov = load_provenance(prov_path)
    entry = ProvenanceEntry(
        problem_id=problem_id,
        source=FORMAL_CONJECTURES_REPO,
        url=fetch_result.url,
        imported_at=datetime.now(tz=UTC),
        sha256=fetch_result.sha256,
        remote_etag=fetch_result.etag,
    )
    prov.upsert(entry)
    save_provenance(prov_path, prov)


def _build_import_data(
    problem_id: int,
    local_path: Path,
    cache_path: Path,
    fetch_url: str,
    fetch_sha256: str,
    *,
    dry_run: bool,
    written: bool,
    lean_validated: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build common import result data dict."""
    data: dict[str, Any] = {
        "problem_id": problem_id,
        "dry_run": dry_run,
        "written": written,
        "path": str(local_path),
        "cache_path": str(cache_path),
        "source": FORMAL_CONJECTURES_REPO,
        "url": fetch_url,
        "sha256": fetch_sha256,
        "lean_validated": lean_validated,
    }
    if reason:
        data["reason"] = reason
    return data


def _check_local_conflict(
    local_path: Path, fetch_sha256: str, force: bool
) -> str | None:
    """Check for local file conflict. Returns error message if conflict, None if OK."""
    if not local_path.exists() or force:
        return None
    local_info = LocalFormalizationInfo.from_file(local_path)
    if local_info.sha256 == fetch_sha256:
        return "same_content"
    return f"Local file exists with different content: {local_path}. Use --force to overwrite."


def _do_import(
    problem_id: int,
    project_path: Path,
    fetch_result: Any,
    local_path: Path,
    cache_path: Path,
    *,
    force: bool,
    dry_run: bool,
    skip_lean_validation: bool,
) -> CLIOutput:
    """Execute the import operation. Extracted to reduce return statement count."""
    # Check for conflicts
    conflict = _check_local_conflict(local_path, fetch_result.sha256, force)
    if conflict == "same_content":
        return CLIOutput.ok(
            command="erdos lean import",
            data=_build_import_data(
                problem_id,
                local_path,
                cache_path,
                fetch_result.url,
                fetch_result.sha256,
                dry_run=dry_run,
                written=False,
                lean_validated=False,
                reason="already_imported",
            ),
        )
    if conflict:
        return CLIOutput.err(
            command="erdos lean import",
            error_type="Conflict",
            message=conflict,
            code=ExitCode.ERROR,
        )

    if dry_run:
        return CLIOutput.ok(
            command="erdos lean import",
            data=_build_import_data(
                problem_id,
                local_path,
                cache_path,
                fetch_result.url,
                fetch_result.sha256,
                dry_run=True,
                written=False,
                lean_validated=False,
            ),
        )

    # Write file and validate
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(fetch_result.content, encoding="utf-8")
    lean_validated = _validate_imported_file(
        project_path, local_path, skip_lean_validation
    )
    if isinstance(lean_validated, CLIOutput):
        return lean_validated  # Validation error

    # Update provenance
    _update_provenance(local_path, problem_id, fetch_result)

    return CLIOutput.ok(
        command="erdos lean import",
        data=_build_import_data(
            problem_id,
            local_path,
            cache_path,
            fetch_result.url,
            fetch_result.sha256,
            dry_run=False,
            written=True,
            lean_validated=lean_validated,
        ),
    )


def import_upstream_formalization(
    problem_id: int,
    project_path: Path,
    *,
    source_url: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    no_network: bool = False,
    skip_lean_validation: bool = False,
) -> CLIOutput:
    """Import upstream formalization for a problem."""
    try:
        fetch_result = fetch_upstream_lean_file(
            project_path, problem_id, source_url=source_url, no_network=no_network
        )
        local_path = get_local_file_path(project_path, problem_id)
        cache_path = get_cache_path(project_path, problem_id)
        return _do_import(
            problem_id,
            project_path,
            fetch_result,
            local_path,
            cache_path,
            force=force,
            dry_run=dry_run,
            skip_lean_validation=skip_lean_validation,
        )
    except FormalConjecturesError as e:
        error_type_to_exit_code = {
            "NetworkError": ExitCode.NETWORK_ERROR,
            "NotFound": ExitCode.NOT_FOUND,
            "ConfigError": ExitCode.CONFIG_ERROR,
        }
        exit_code = error_type_to_exit_code.get(e.error_type, ExitCode.ERROR)
        return CLIOutput.err(
            command="erdos lean import",
            error_type=e.error_type,
            message=str(e),
            code=exit_code,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean import command")
        return CLIOutput.err(
            command="erdos lean import",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


def prove_with_aristotle(
    input_file: Path,
    output_file: Path,
    *,
    timeout: int = 600,
    informal: bool = False,
    formal_input_context: bool = False,
) -> CLIOutput:
    """Run Aristotle prove-from-file command.

    Args:
        input_file: Path to the input Lean file
        output_file: Path for the output Lean file
        timeout: Maximum seconds to wait for completion
        informal: Pass --informal flag to Aristotle
        formal_input_context: Pass --formal-input-context flag to Aristotle

    Returns:
        CLIOutput with execution details
    """
    try:
        result = run_aristotle_prove_from_file(
            input_file,
            output_file,
            timeout=timeout,
            informal=informal,
            formal_input_context=formal_input_context,
        )
        if result.success:
            return CLIOutput.ok(
                command="erdos lean prove",
                data=result.to_dict(),
            )
        else:
            # Nonzero exit code - return error with stderr
            return CLIOutput.err(
                command="erdos lean prove",
                error_type="AristotleError",
                message=result.stderr
                or f"Aristotle exited with code {result.exit_code}",
                code=ExitCode.ERROR,
            )
    except AristotleError as e:
        # Map error types to exit codes
        error_type_to_exit_code = {
            "ConfigError": ExitCode.CONFIG_ERROR,
            "NotFound": ExitCode.NOT_FOUND,
            "UsageError": ExitCode.USAGE_ERROR,
            "Timeout": ExitCode.ERROR,
        }
        exit_code = error_type_to_exit_code.get(e.error_type, ExitCode.ERROR)
        return CLIOutput.err(
            command="erdos lean prove",
            error_type=e.error_type,
            message=str(e),
            code=exit_code,
        )
    except Exception as e:
        logger.exception("Unexpected error in lean prove command")
        return CLIOutput.err(
            command="erdos lean prove",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


# ============================================================================
# Batch Formalize (SPEC-015)
# ============================================================================

err_console = Console(stderr=True)


def _formalize_single_problem(
    problem_id: int,
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
    skip_existing: bool,
) -> tuple[int, bool, str]:
    """Formalize a single problem (for batch mode).

    Returns:
        Tuple of (problem_id, success, message)
    """
    # Check if file exists
    local_path = get_local_file_path(project_path, problem_id)
    if skip_existing and local_path.exists():
        return (problem_id, True, "skipped (exists)")

    result = formalize_problem(problem_id, project_path, repo=repo, force=force)
    if result.success:
        return (problem_id, True, "OK")
    else:
        msg = (
            result.error.get("message", "unknown")
            if isinstance(result.error, dict)
            else "failed"
        )
        return (problem_id, False, msg)


def batch_formalize(
    problem_ids: list[int],
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool = False,
    skip_existing: bool = False,
    max_concurrent: int = 4,
    on_progress: Any | None = None,
) -> BatchResult:
    """Batch formalize multiple problems with optional parallelism.

    Args:
        problem_ids: List of problem IDs to formalize
        project_path: Path to Lean project
        repo: Problem repository
        force: Overwrite existing files
        skip_existing: Skip problems that already have Lean files
        max_concurrent: Max parallel Lean compilations (default: 4)
        on_progress: Callback for progress updates

    Returns:
        BatchResult with outcome details
    """
    batch_id = generate_batch_id()
    completed: list[int] = []
    failed: list[int] = []
    total = len(problem_ids)

    with measure_time_ms() as duration:
        if max_concurrent == 1:
            # Sequential execution
            for i, problem_id in enumerate(problem_ids):
                pid, success, message = _formalize_single_problem(
                    problem_id,
                    project_path,
                    repo=repo,
                    force=force,
                    skip_existing=skip_existing,
                )
                if success:
                    completed.append(pid)
                else:
                    failed.append(pid)

                if on_progress:
                    on_progress(
                        BatchProgress(
                            problem_id=pid,
                            index=i,
                            total=total,
                            success=success,
                            message=message,
                        )
                    )
        else:
            # Parallel execution using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = {
                    executor.submit(
                        _formalize_single_problem,
                        pid,
                        project_path,
                        repo=repo,
                        force=force,
                        skip_existing=skip_existing,
                    ): pid
                    for pid in problem_ids
                }

                for i, future in enumerate(as_completed(futures)):
                    pid, success, message = future.result()
                    if success:
                        completed.append(pid)
                    else:
                        failed.append(pid)

                    if on_progress:
                        on_progress(
                            BatchProgress(
                                problem_id=pid,
                                index=i,
                                total=total,
                                success=success,
                                message=message,
                            )
                        )

    return BatchResult(
        batch_id=batch_id,
        total=total,
        completed_count=len(completed),
        failed_count=len(failed),
        failed_ids=failed,
        duration_ms=duration[0],
    )


def _print_human_batch_formalize(result_data: dict[str, Any]) -> None:
    """Pretty-print batch formalize results."""
    batch_id = result_data.get("batch_id", "?")
    total = result_data.get("total", 0)
    completed = result_data.get("completed", 0)
    failed = result_data.get("failed", 0)
    failed_ids = result_data.get("failed_ids", [])
    dry_run = result_data.get("dry_run", False)

    if dry_run:
        console.print(f"\n[yellow]Dry run[/yellow]: Would formalize {total} problems")
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


def _batch_result_to_cli_output_formalize(
    result: BatchResult, problem_ids: list[int], dry_run: bool
) -> CLIOutput:
    """Convert BatchResult to CLIOutput for formalize command."""
    if result.exit_code != ExitCode.SUCCESS:
        return CLIOutput.err(
            command="erdos lean formalize",
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
        "dry_run": dry_run,
    }

    if dry_run:
        data["problem_ids"] = problem_ids

    if result.failed_count > 0:
        output = CLIOutput.ok(command="erdos lean formalize", data=data)
        output.success = False
        return output

    return CLIOutput.ok(command="erdos lean formalize", data=data)


# ============================================================================
# CLI Commands
# ============================================================================


@app.command()
def init(
    ctx: typer.Context,
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    no_mathlib: Annotated[
        bool,
        typer.Option("--no-mathlib", help="Skip fetching mathlib"),
    ] = False,
) -> None:
    """
    Initialize Lean 4 project with mathlib.

    Creates lakefile.lean, lean-toolchain, and directory structure.
    """

    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        path.mkdir(parents=True, exist_ok=True)
        result = init_lean_project(path, fetch_mathlib=not no_mathlib)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


@app.command()
def check(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(
            help="Lean file to check.",
            exists=True,
            readable=True,
        ),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
) -> None:
    """
    Check a Lean file for compilation errors.

    Example: erdos lean check Erdos/Problem006.lean
    """
    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        result = check_lean_file(file, path)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)

    if (
        result.success
        and isinstance(result.data, dict)
        and not result.data.get("success", True)
    ):
        raise typer.Exit(code=ExitCode.LEAN_ERROR)


def _is_batch_formalize_mode(
    problem_id: int | None,
    all_problems: bool,
    status: str | None,
    tag: list[str] | None,
) -> bool:
    """Determine if batch mode should be activated for formalize."""
    if all_problems:
        return True
    if problem_id is None:
        return bool(status is not None or tag)
    return False


def _run_batch_formalize(
    problem_ids: list[int],
    project_path: Path,
    *,
    repo: ProblemRepository,
    force: bool,
    skip_existing: bool,
    max_concurrent: int,
    dry_run: bool,
    json_mode: bool,
) -> CLIOutput:
    """Execute batch formalize logic."""
    if dry_run:
        # Just show what would be processed
        data = {
            "batch_id": "",
            "mode": "batch",
            "total": len(problem_ids),
            "completed": 0,
            "failed": 0,
            "failed_ids": [],
            "dry_run": True,
            "problem_ids": problem_ids,
        }
        return CLIOutput.ok(command="erdos lean formalize", data=data)

    # Progress callback for human output
    def on_progress(progress: BatchProgress) -> None:
        status_icon = "[green]✓[/green]" if progress.success else "[red]✗[/red]"
        err_console.print(
            f"[{progress.index + 1}/{progress.total}] Problem {progress.problem_id}... "
            f"{status_icon} ({progress.message})"
        )

    result = batch_formalize(
        problem_ids,
        project_path,
        repo=repo,
        force=force,
        skip_existing=skip_existing,
        max_concurrent=max_concurrent,
        on_progress=None if json_mode else on_progress,
    )

    return _batch_result_to_cli_output_formalize(result, problem_ids, dry_run)


@app.command()
def formalize(
    ctx: typer.Context,
    problem_id: Annotated[
        int | None,
        typer.Argument(
            help="Problem ID to formalize (omit for batch mode).",
            min=1,
        ),
    ] = None,
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing file"),
    ] = False,
    import_upstream: Annotated[
        bool,
        typer.Option(
            "--import-upstream",
            help="Import upstream formalization instead of generating skeleton",
        ),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option(
            "--no-network",
            help="Use cached upstream file only (requires --import-upstream)",
        ),
    ] = False,
    # Batch options (SPEC-015)
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
    tag: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by tag (can be repeated)"),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Max problems to process"),
    ] = None,
    skip_existing: Annotated[
        bool,
        typer.Option("--skip-existing", help="Skip problems with existing Lean files"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be processed"),
    ] = False,
    max_concurrent: Annotated[
        int,
        typer.Option(
            "--max-concurrent", help="Max parallel Lean compilations (default: 4)"
        ),
    ] = 4,
) -> None:
    """
    Generate Lean skeletons for problems.

    Single mode: Pass a PROBLEM_ID to formalize one problem.

    Batch mode: Omit PROBLEM_ID and use --all or filter options (--status, --tag)
    to process multiple problems. Supports parallel execution with --max-concurrent.

    Use --import-upstream to import existing formalizations instead.
    """
    json_mode = bool((ctx.obj or {}).get("json"))

    # Determine mode
    batch_mode = _is_batch_formalize_mode(problem_id, all_problems, status, tag)

    # Validate: need problem_id or batch filters
    if not batch_mode and problem_id is None:
        result = CLIOutput.err(
            command="erdos lean formalize",
            error_type="UsageError",
            message="Provide a PROBLEM_ID or use batch options (--all, --status, --tag)",
            code=ExitCode.USAGE_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos lean formalize")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)

        path = project_path or Path("formal/lean")

        if batch_mode:
            # Batch formalize
            filters = BatchFilters(
                status=status,
                tags=tag,
                limit=limit,
            )
            problems = app_ctx.problems.load_all()
            problem_ids_to_process = filter_problem_ids(problems, filters)

            if not problem_ids_to_process:
                result = CLIOutput.err(
                    command="erdos lean formalize",
                    error_type="NotFoundError",
                    message="No problems match the given filters",
                    code=ExitCode.NOT_FOUND,
                )
            else:
                result = _run_batch_formalize(
                    problem_ids_to_process,
                    path,
                    repo=app_ctx.problems,
                    force=force,
                    skip_existing=skip_existing,
                    max_concurrent=max_concurrent,
                    dry_run=dry_run,
                    json_mode=json_mode,
                )
        elif problem_id is not None and import_upstream:
            # Import upstream formalization (single problem)
            result = import_upstream_formalization(
                problem_id,
                path,
                force=force,
                no_network=no_network,
                skip_lean_validation=True,  # Skip validation for formalize
            )
        elif problem_id is not None:
            # Single problem formalize
            result = formalize_problem(
                problem_id,
                path,
                repo=app_ctx.problems,
                force=force,
            )
        else:
            # Should be unreachable due to earlier validation
            result = CLIOutput.err(
                command="erdos lean formalize",
                error_type="UsageError",
                message="Provide a PROBLEM_ID or use batch options",
                code=ExitCode.USAGE_ERROR,
            )

    result.duration_ms = duration[0]

    # Use appropriate human printer
    print_fn = _print_human_batch_formalize if batch_mode else _print_human
    exit_with_result(ctx, result, print_human=print_fn)


@app.command()
def prove(
    ctx: typer.Context,
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Lean file to prove.",
            exists=True,
            readable=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (required; must differ from input).",
        ),
    ],
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            "-t",
            help="Maximum seconds to wait for completion.",
        ),
    ] = 600,
    informal: Annotated[
        bool,
        typer.Option("--informal", help="Pass --informal flag to Aristotle."),
    ] = False,
    formal_input_context: Annotated[
        bool,
        typer.Option(
            "--formal-input-context",
            help="Pass --formal-input-context flag to Aristotle.",
        ),
    ] = False,
) -> None:
    """
    Run Aristotle prove-from-file on a Lean file.

    Requires ARISTOTLE_API_KEY environment variable to be set.
    Writes output to a separate file (never overwrites the input).

    Example: erdos lean prove Problem006.lean --output Problem006.solved.lean
    """
    # Validate output is not the same as input
    if input_file.resolve() == output.resolve():
        result = CLIOutput.err(
            command="erdos lean prove",
            error_type="UsageError",
            message="Output file cannot be the same as input file.",
            code=ExitCode.USAGE_ERROR,
        )
        exit_with_result(ctx, result, print_human=_print_human)
        return

    with measure_time_ms() as duration:
        result = prove_with_aristotle(
            input_file,
            output,
            timeout=timeout,
            informal=informal,
            formal_input_context=formal_input_context,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


@app.command()
def status(
    ctx: typer.Context,
    problem_id: Annotated[
        int | None,
        typer.Argument(
            help="Problem ID (optional; shows summary if omitted).",
            min=1,
        ),
    ] = None,
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    upstream: Annotated[
        bool,
        typer.Option(
            "--upstream", help="Check upstream metadata for formalization status"
        ),
    ] = False,
    local: Annotated[
        bool,
        typer.Option("--local", help="Check local formal/lean/Erdos/ directory"),
    ] = False,
) -> None:
    """
    Show formalization status for problems.

    Without PROBLEM_ID, shows summary counts.
    With PROBLEM_ID, shows detailed status for that problem.

    Example: erdos lean status 6
    """
    with measure_time_ms() as duration:
        app_ctx, app_error = get_app_context(ctx, command="erdos lean status")
        if app_error is not None:
            exit_with_result(ctx, app_error)
            return
        if app_ctx is None:
            return

        path = project_path or Path("formal/lean")

        # Default: check both if neither specified
        check_upstream = upstream or not (upstream or local)
        check_local = local or not (upstream or local)

        result = get_formalization_status(
            problem_id,
            path,
            repo=app_ctx.problems,
            check_upstream=check_upstream,
            check_local=check_local,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)


@app.command(name="import")
def import_cmd(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to import formalization for.",
            min=1,
        ),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/)",
        ),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", help="Override source URL"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing local file"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be imported without writing"),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option("--no-network", help="Use cached upstream file only"),
    ] = False,
    skip_lean_validation: Annotated[
        bool,
        typer.Option(
            "--skip-lean-validation",
            help="Do not run Lean check on imported file",
        ),
    ] = False,
) -> None:
    """
    Import upstream formalization for a problem.

    Fetches from google-deepmind/formal-conjectures by default.

    Example: erdos lean import 6
    """
    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        result = import_upstream_formalization(
            problem_id,
            path,
            source_url=source,
            force=force,
            dry_run=dry_run,
            no_network=no_network,
            skip_lean_validation=skip_lean_validation,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
