"""erdos sync statements - sync Lean statements from DeepMind (SPEC-035).

This is a thin wrapper around `erdos lean import` that exists so
`erdos sync all` can orchestrate the full sync pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

import typer

from erdos.commands.lean.import_cmd import import_upstream_formalization
from erdos.commands.presenter import console, exit_with_result
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print sync statements result."""
    problem_id = data.get("problem_id")
    written = data.get("written", False)
    dry_run = data.get("dry_run", False)
    reason = data.get("reason")
    path = data.get("path", "")

    if dry_run:
        console.print(f"[dim]Would import[/dim] statement for problem #{problem_id}")
        console.print(f"  Target: {path}")
    elif written:
        console.print(f"[green]Imported[/green] statement for problem #{problem_id}")
        console.print(f"  Path: {path}")
    elif reason == "already_imported":
        console.print(f"[dim]Up to date[/dim]: problem #{problem_id} already imported")
    else:
        console.print(f"Problem #{problem_id}: see JSON output for details")


def statements(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(help="Problem ID to sync statement for.", min=1),
    ],
    project_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            "-p",
            help="Path to Lean project (default: formal/lean/).",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite local modifications."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without writing."),
    ] = False,
    no_network: Annotated[
        bool,
        typer.Option("--no-network", help="Use only cached upstream data."),
    ] = False,
    skip_lean_validation: Annotated[
        bool,
        typer.Option(
            "--skip-lean-validation",
            help="Do not run Lean check on imported file.",
        ),
    ] = False,
) -> None:
    """Sync Lean statement from DeepMind formal-conjectures.

    This wraps `erdos lean import` for use in the sync orchestration layer.
    The statement is imported from google-deepmind/formal-conjectures into
    formal/lean/Erdos/Problem{ID}.lean.

    Examples:
        erdos sync statements 347
        erdos sync statements 347 --force
        erdos sync statements 347 --dry-run
    """
    with measure_time_ms() as duration:
        path = project_path or Path("formal/lean")
        result = import_upstream_formalization(
            problem_id,
            path,
            force=force,
            dry_run=dry_run,
            no_network=no_network,
            skip_lean_validation=skip_lean_validation,
        )

    # Override command name for consistency
    result.command = "erdos sync statements"
    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
