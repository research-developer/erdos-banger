"""erdos sync all - orchestrate all sync operations (SPEC-035).

This command runs all sync operations in the correct order:
1. submodule - Update teorth/erdosproblems submodule
2. website - Fetch data from erdosproblems.com
3. proof - Extract proof repository links
4. statements - Import Lean statements from DeepMind
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from erdos.commands.lean.import_cmd import import_upstream_formalization
from erdos.commands.presenter import exit_with_result
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.sync import (
    SubmoduleSyncStatus,
    fetch_and_parse_problem,
    get_submodule_path,
    update_submodule,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)
console = Console()


def _print_step_result(name: str, step_data: dict[str, Any]) -> None:
    """Print a single step result."""
    if not step_data.get("success"):
        console.print(f"[red]\u2717[/red] {name}: {step_data.get('error', '')}")
        return

    if step_data.get("skipped"):
        console.print(
            f"[dim]\u2713[/dim] {name}: skipped ({step_data.get('reason', '')})"
        )
        return

    # Step-specific success messages
    if name == "Submodule" and step_data.get("updated"):
        old_c = step_data.get("old_commit", "")[:8]
        new_c = step_data.get("new_commit", "")[:8]
        console.print(f"[green]\u2713[/green] {name} updated: {old_c} -> {new_c}")
    elif name == "Submodule":
        console.print(
            f"[dim]\u2713[/dim] {name} up to date: {step_data.get('commit', '')[:8]}"
        )
    elif name == "Website":
        console.print(
            f"[green]\u2713[/green] {name}: {step_data.get('fetched', 0)} problems fetched"
        )
    elif name == "Proof":
        console.print(
            f"[green]\u2713[/green] {name}: {step_data.get('proofs_found', 0)} repos found"
        )
    elif name == "Statements":
        imported = step_data.get("imported", 0)
        skipped = step_data.get("skipped_count", 0)
        console.print(
            f"[green]\u2713[/green] {name}: {imported} imported, {skipped} skipped"
        )


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print sync all results."""
    console.print("[bold]Sync All Results[/bold]")
    console.print()

    _print_step_result("Submodule", data.get("submodule", {}))
    _print_step_result("Website", data.get("website", {}))
    _print_step_result("Proof", data.get("proof", {}))
    _print_step_result("Statements", data.get("statements", {}))

    # Summary
    console.print()
    errors = data.get("errors", [])
    if errors:
        console.print(f"[yellow]Completed with {len(errors)} error(s)[/yellow]")
    else:
        console.print("[green]All sync operations completed successfully[/green]")


def _sync_submodule(no_network: bool) -> dict[str, Any]:
    """Run submodule sync."""
    if no_network:
        return {"success": True, "skipped": True, "reason": "no_network"}

    try:
        submodule_path = get_submodule_path()
        status: SubmoduleSyncStatus = update_submodule(submodule_path)
        updated = (
            status.previous_commit_hash is not None
            and status.previous_commit_hash != status.commit_hash
        )
        return {
            "success": True,
            "updated": updated,
            "commit": status.commit_hash or "",
            "old_commit": status.previous_commit_hash or "",
            "new_commit": status.commit_hash or "",
        }
    except Exception as e:
        logger.warning("Submodule sync failed: %s", e)
        return {"success": False, "error": str(e)}


def _sync_website(
    problem_ids: list[int] | None,
    no_network: bool,
) -> dict[str, Any]:
    """Run website sync for specified problems."""
    if no_network:
        return {"success": True, "skipped": True, "reason": "no_network"}
    if not problem_ids:
        return {"success": True, "skipped": True, "reason": "no_problem_ids"}

    fetched = 0
    errors: list[str] = []
    for pid in problem_ids:
        try:
            fetch_and_parse_problem(pid)
            fetched += 1
        except Exception as e:
            errors.append(f"Problem {pid}: {e}")
            logger.warning("Website sync failed for problem %d: %s", pid, e)

    return {
        "success": len(errors) == 0,
        "fetched": fetched,
        "errors": errors,
    }


def _sync_statements(
    problem_ids: list[int] | None,
    project_path: Path,
    force: bool,
    no_network: bool,
) -> dict[str, Any]:
    """Run statement imports for specified problems."""
    if not problem_ids:
        return {"success": True, "skipped": True, "reason": "no_problem_ids"}

    imported = 0
    skipped_count = 0
    errors: list[str] = []

    for pid in problem_ids:
        try:
            result = import_upstream_formalization(
                pid,
                project_path,
                force=force,
                no_network=no_network,
            )
            if result.success:
                if result.data and result.data.get("written"):
                    imported += 1
                else:
                    skipped_count += 1
            else:
                # Check error code - NOT_FOUND is OK (not all problems have statements)
                error_code = result.error.get("code") if result.error else None
                if error_code == ExitCode.NOT_FOUND:
                    skipped_count += 1
                else:
                    error_msg = result.error.get("message", "") if result.error else ""
                    errors.append(f"Problem {pid}: {error_msg}")
        except Exception as e:
            errors.append(f"Problem {pid}: {e}")
            logger.warning("Statement import failed for problem %d: %s", pid, e)

    return {
        "success": len(errors) == 0,
        "imported": imported,
        "skipped_count": skipped_count,
        "errors": errors,
    }


def _run_sync_pipeline(
    pids: list[int] | None,
    lean_path: Path,
    force: bool,
    no_network: bool,
    skip_submodule: bool,
    skip_website: bool,
    skip_proof: bool,
    skip_statements: bool,
) -> dict[str, Any]:
    """Execute the sync pipeline and return results."""
    all_errors: list[str] = []
    skip_result: dict[str, Any] = {
        "success": True,
        "skipped": True,
        "reason": "skip_flag",
    }

    # 1. Submodule
    submodule_result = (
        skip_result.copy() if skip_submodule else _sync_submodule(no_network)
    )
    if not submodule_result.get("success"):
        all_errors.append(f"submodule: {submodule_result.get('error', '')}")

    # 2. Website
    website_result = (
        skip_result.copy() if skip_website else _sync_website(pids, no_network)
    )
    if not website_result.get("success"):
        all_errors.extend([f"website: {e}" for e in website_result.get("errors", [])])

    # 3. Proof (always deferred to explicit `erdos sync proof` for now)
    proof_result: dict[str, Any] = (
        skip_result.copy()
        if skip_proof
        else {
            "success": True,
            "skipped": True,
            "reason": "use_erdos_sync_proof",
            "proofs_found": 0,
        }
    )

    # 4. Statements
    statements_result = (
        skip_result.copy()
        if skip_statements
        else _sync_statements(pids, lean_path, force, no_network)
    )
    if not statements_result.get("success"):
        all_errors.extend(
            [f"statements: {e}" for e in statements_result.get("errors", [])]
        )

    return {
        "submodule": submodule_result,
        "website": website_result,
        "proof": proof_result,
        "statements": statements_result,
        "errors": all_errors,
        "problem_ids": pids,
    }


def sync_all(
    ctx: typer.Context,
    problem_ids: Annotated[
        str | None,
        typer.Option(
            "--problems",
            "-p",
            help="Comma-separated problem IDs to sync (default: submodule only).",
        ),
    ] = None,
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--lean-path",
            help="Path to Lean project (default: formal/lean/).",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite local modifications."),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option("--no-network", help="Use only cached data (submodule skipped)."),
    ] = False,
    skip_submodule: Annotated[
        bool,
        typer.Option("--skip-submodule", help="Skip submodule update."),
    ] = False,
    skip_website: Annotated[
        bool,
        typer.Option("--skip-website", help="Skip website fetch."),
    ] = False,
    skip_proof: Annotated[
        bool,
        typer.Option("--skip-proof", help="Skip proof link extraction."),
    ] = False,
    skip_statements: Annotated[
        bool,
        typer.Option("--skip-statements", help="Skip Lean statement import."),
    ] = False,
) -> None:
    """Run all sync operations in sequence.

    By default, only updates the submodule. Specify --problems to sync
    specific problems from website, proof links, and statements.

    The operations run in this order:
    1. submodule - Update teorth/erdosproblems submodule
    2. website - Fetch data from erdosproblems.com
    3. proof - Extract proof repository links (not yet in 'all')
    4. statements - Import Lean statements from DeepMind

    Examples:
        erdos sync all                      # Update submodule only
        erdos sync all --problems 6,347     # Sync problems 6 and 347
        erdos sync all --skip-statements    # Skip Lean imports
    """
    command = "erdos sync all"

    # Parse problem IDs
    pids: list[int] | None = None
    if problem_ids:
        try:
            pids = [int(p.strip()) for p in problem_ids.split(",") if p.strip()]
        except ValueError as e:
            exit_with_result(
                ctx,
                CLIOutput.err(
                    command=command,
                    error_type="ValueError",
                    message=f"Invalid problem ID: {e}",
                    code=ExitCode.USAGE_ERROR,
                ),
            )
            return

    with measure_time_ms() as duration:
        lean_path = project_path or Path("formal/lean")
        output_data = _run_sync_pipeline(
            pids,
            lean_path,
            force,
            no_network,
            skip_submodule,
            skip_website,
            skip_proof,
            skip_statements,
        )
        result = CLIOutput.ok(command=command, data=output_data)

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
