"""erdos sync submodule - sync teorth/erdosproblems submodule (SPEC-035/3)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel

from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.sync.dataset import load_enriched_problems, save_enriched_problems
from erdos.core.sync.merge import merge_problem_data
from erdos.core.sync.submodule import (
    SubmoduleCheckError,
    SubmoduleFetchError,
    SubmoduleNotInitializedError,
    get_submodule_commit,
    get_submodule_path,
    load_submodule_problems,
    update_submodule,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)
console = Console()


# =============================================================================
# Data paths
# =============================================================================

SYNC_CACHE_PATH = Path("data/sync_cache")
DEFAULT_DATA_PATH = Path("data/problems_enriched.yaml")


def _ensure_cache_dir() -> None:
    """Ensure sync cache directory exists."""
    SYNC_CACHE_PATH.mkdir(parents=True, exist_ok=True)


def _save_sync_status(status_data: dict[str, Any]) -> None:
    """Save submodule sync status to cache."""
    _ensure_cache_dir()
    status_path = SYNC_CACHE_PATH / "submodule_status.json"
    tmp_path = status_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, default=str)
    tmp_path.replace(status_path)


def _merge_submodule_metadata(
    submodule_path: Path,
    *,
    data_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    """Merge submodule metadata into the local enriched dataset (best-effort).

    This updates only fields that are submodule-authoritative per SPEC-035:
    status, prize, tags, formalized, oeis_ids.
    """
    # Only merge if the dataset exists; we cannot synthesize title/statement.
    if not data_path.exists():
        return {"success": True, "skipped": True, "reason": "no_local_dataset"}

    existing = load_enriched_problems(data_path)
    if not existing:
        return {"success": True, "skipped": True, "reason": "empty_local_dataset"}

    try:
        submodule_problems = load_submodule_problems(submodule_path)
    except Exception as e:
        logger.warning("Failed to load submodule problems for merge: %s", e)
        return {"success": False, "error": str(e)}

    updated_records = 0
    missing_required_fields = 0

    for pid, existing_record in existing.items():
        sub_data = submodule_problems.get(pid)
        if sub_data is None:
            continue

        merged = merge_problem_data(pid, submodule=sub_data, existing=existing_record)
        if merged is None:
            missing_required_fields += 1
            continue

        if merged.model_dump(mode="json") != existing_record.model_dump(mode="json"):
            existing[pid] = merged
            updated_records += 1

    if not dry_run and updated_records > 0:
        save_enriched_problems(data_path, existing)

    return {
        "success": True,
        "updated_records": updated_records,
        "missing_required_fields": missing_required_fields,
        "dry_run": dry_run,
        "data_path": str(data_path),
    }


# =============================================================================
# Core logic
# =============================================================================


def sync_submodule(
    *,
    check_only: bool = False,
    submodule_path: Path | None = None,
    data_path: Path | None = None,
    dry_run: bool = False,
) -> CLIOutput:
    """
    Sync or check the submodule.

    Args:
        check_only: If True, only check staleness without updating
        submodule_path: Override path (for testing)

    Returns:
        CLIOutput with sync result
    """
    if submodule_path is None:
        submodule_path = get_submodule_path()
    if data_path is None:
        data_path = DEFAULT_DATA_PATH

    try:
        # Get current commit before any operation
        try:
            get_submodule_commit(submodule_path)
        except SubmoduleNotInitializedError as e:
            return CLIOutput.err(
                command="erdos sync submodule",
                error_type="NotInitializedError",
                message=str(e),
                code=ExitCode.ERROR,
            )

        # Perform sync or check
        status = update_submodule(submodule_path, check_only=check_only)

        # Count problems for status
        problems_count = 0
        try:
            problems = load_submodule_problems(submodule_path)
            problems_count = len(problems)
            status = status.model_copy(update={"problems_count": problems_count})
        except Exception as e:
            logger.warning("Failed to count problems: %s", e)

        # Save status to cache (skip in dry-run mode)
        if not dry_run:
            _save_sync_status(status.model_dump(mode="json"))

        merge_result: dict[str, Any] | None = None
        if not check_only:
            merge_result = _merge_submodule_metadata(
                submodule_path, data_path=data_path, dry_run=dry_run
            )

        # Build response
        updated = (
            status.previous_commit_hash != status.commit_hash
            if status.previous_commit_hash
            else False
        )

        return CLIOutput.ok(
            command="erdos sync submodule",
            data={
                "checked": check_only,
                "dry_run": dry_run,
                "updated": updated,
                "previous_commit": status.previous_commit_hash,
                "current_commit": status.commit_hash,
                "stale": status.stale,
                "problems_count": problems_count,
                "merge": merge_result,
            },
        )

    except SubmoduleFetchError as e:
        return CLIOutput.err(
            command="erdos sync submodule",
            error_type="FetchError",
            message=str(e),
            code=ExitCode.NETWORK_ERROR,
        )
    except SubmoduleCheckError as e:
        return CLIOutput.err(
            command="erdos sync submodule",
            error_type="CheckError",
            message=str(e),
            code=ExitCode.NETWORK_ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in sync submodule")
        return CLIOutput.err(
            command="erdos sync submodule",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )


# =============================================================================
# Human output
# =============================================================================


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print sync result for humans."""
    checked = data.get("checked", False)
    updated = data.get("updated", False)
    prev_commit = data.get("previous_commit")
    curr_commit = data.get("current_commit")
    stale = data.get("stale")
    problems_count = data.get("problems_count", 0)

    if checked:
        # Check-only mode
        if stale is True:
            status_icon = "\u26a0"  # Warning
            status_text = "[yellow]Submodule is stale (behind remote)[/yellow]"
        elif stale is False:
            status_icon = "\u2713"
            status_text = "[green]Submodule is up to date[/green]"
        else:
            status_icon = "?"
            status_text = "[dim]Could not determine staleness[/dim]"

        lines = [
            "[bold]Submodule Check[/bold]",
            status_text,
            f"Current commit: {curr_commit[:12] if curr_commit else 'unknown'}",
            f"Problems: {problems_count:,}",
        ]
    elif updated:
        # Update mode with changes
        status_icon = "\u2713"
        lines = [
            "[bold]Submodule Updated[/bold]",
            f"Previous: {prev_commit[:12] if prev_commit else 'unknown'}",
            f"Current:  {curr_commit[:12] if curr_commit else 'unknown'}",
            f"Problems: {problems_count:,}",
        ]
    else:
        # Update mode without changes
        status_icon = "-"
        lines = [
            "[bold]Submodule[/bold]",
            "[dim]No changes (already up to date)[/dim]",
            f"Commit: {curr_commit[:12] if curr_commit else 'unknown'}",
            f"Problems: {problems_count:,}",
        ]

    panel = Panel(
        "\n".join(lines),
        title=f"{status_icon} Sync Result",
        expand=False,
    )
    console.print(panel)


# =============================================================================
# CLI Command
# =============================================================================


def submodule(
    ctx: typer.Context,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help="Only check if submodule is stale (CI-friendly mode, exits 0/1)",
        ),
    ] = False,
) -> None:
    """
    Update the teorth/erdosproblems submodule to latest remote.

    By default, fetches updates from origin and checks out the latest commit.
    Use --check to only verify staleness without updating (useful for CI).

    Examples:
        erdos sync submodule           # Update to latest
        erdos sync submodule --check   # Check if stale (for CI)
    """
    with measure_time_ms() as duration:
        result = sync_submodule(check_only=check)

    result.duration_ms = duration[0]

    # For --check mode, use exit code to indicate staleness
    # We create a new result with the same data but error exit code
    if check and result.success and result.data:
        stale = result.data.get("stale")
        if stale is True:
            # Return stale status as an error for CI to detect
            result = CLIOutput(
                command="erdos sync submodule",
                success=False,
                data=None,
                error={
                    "type": "StaleWarning",
                    "message": "Submodule is stale (behind remote)",
                    "code": ExitCode.ERROR,
                    # Preserve original data in error for machine consumption
                    "original_data": result.data,
                },
                duration_ms=result.duration_ms,
            )

    exit_with_result(ctx, result, print_human=_print_human)
