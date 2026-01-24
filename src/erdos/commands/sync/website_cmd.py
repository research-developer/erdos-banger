"""erdos sync website - fetch structured data from erdosproblems.com (SPEC-035)."""

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
from erdos.core.models import CLIOutput, ProblemRecord
from erdos.core.sync.dataset import load_enriched_problems, save_enriched_problems
from erdos.core.sync.merge import merge_problem_data
from erdos.core.sync.submodule import get_submodule_path, load_submodule_problems
from erdos.core.sync.website import (
    WebsiteFetchError,
    WebsiteParseError,
    fetch_and_parse_problem,
    fetch_latex_source,
    parse_problem_html,
    save_latex_source,
)
from erdos.core.timing import measure_time_ms


logger = logging.getLogger(__name__)
console = Console()


# =============================================================================
# Data paths
# =============================================================================

DEFAULT_DATA_PATH = Path("data/problems_enriched.yaml")
SYNC_CACHE_PATH = Path("data/sync_cache/website")


def _ensure_data_dir() -> None:
    """Ensure data directories exist."""
    DEFAULT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYNC_CACHE_PATH.mkdir(parents=True, exist_ok=True)


def _load_existing_problems() -> dict[int, ProblemRecord]:
    """Load existing problems from the enriched YAML file."""
    return load_enriched_problems(DEFAULT_DATA_PATH)


def _save_problems(problems: dict[int, ProblemRecord]) -> None:
    """Save problems to the enriched YAML file (atomic write)."""
    _ensure_data_dir()
    save_enriched_problems(DEFAULT_DATA_PATH, problems)


def _save_sync_status(problem_id: int, status_data: dict[str, Any]) -> None:
    """Save sync status to cache."""
    _ensure_data_dir()
    status_path = SYNC_CACHE_PATH / f"{problem_id}.json"
    tmp_path = status_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, default=str)
    tmp_path.replace(status_path)


# =============================================================================
# Core logic
# =============================================================================


def _fetch_website_data(
    problem_id: int,
    html_content: str | None,
    warnings: list[str],
) -> tuple[Any, Any | None]:
    """Fetch or parse website data, handling cache/network modes."""
    if html_content is not None:
        return parse_problem_html(html_content, problem_id), None

    website_data, sync_status = fetch_and_parse_problem(problem_id)
    warnings.extend(sync_status.warnings)
    return website_data, sync_status


def _check_updated(existing: ProblemRecord | None, merged: ProblemRecord) -> bool:
    """Check if problem data has changed."""
    if existing is None:
        return True
    return existing.model_dump(mode="json") != merged.model_dump(mode="json")


def _handle_latex(
    problem_id: int, fetch_latex: bool, dry_run: bool, warnings: list[str]
) -> bool:
    """Handle optional LaTeX fetching."""
    if not fetch_latex or dry_run:
        return False
    latex_content = fetch_latex_source(problem_id)
    if latex_content:
        save_latex_source(problem_id, latex_content)
        return True
    warnings.append("LaTeX source not available")
    return False


def sync_website_problem(
    problem_id: int,
    *,
    fetch_latex: bool = False,
    dry_run: bool = False,
    html_content: str | None = None,
) -> CLIOutput:
    """
    Sync a problem from erdosproblems.com to the local dataset.

    This is the core logic, separated from CLI concerns for testing.

    Args:
        problem_id: Problem ID to sync
        fetch_latex: Whether to also fetch LaTeX source
        dry_run: If True, don't write to disk
        html_content: Pre-fetched HTML (for testing with fixtures)

    Returns:
        CLIOutput with sync result
    """
    warnings: list[str] = []
    cached = html_content is not None

    try:
        website_data, sync_status = _fetch_website_data(
            problem_id, html_content, warnings
        )

        # Best-effort: merge submodule metadata so website-only runs still get status/prize/tags.
        submodule_data = None
        try:
            submodule_path = get_submodule_path()
            submodule_problems = load_submodule_problems(submodule_path)
            submodule_data = submodule_problems.get(problem_id)
        except Exception as e:
            logger.debug("Submodule metadata unavailable: %s", e)

        existing_problems = _load_existing_problems()
        existing = existing_problems.get(problem_id)

        merged = merge_problem_data(
            problem_id,
            submodule=submodule_data,
            website=website_data,
            existing=existing,
        )
        if merged is None:
            return CLIOutput.err(
                command="erdos sync website",
                error_type="MergeError",
                message=f"Problem {problem_id}: missing required fields (title/statement)",
                code=ExitCode.ERROR,
            )

        updated = _check_updated(existing, merged)
        if not dry_run and updated:
            existing_problems[problem_id] = merged
            _save_problems(existing_problems)

        latex_saved = _handle_latex(problem_id, fetch_latex, dry_run, warnings)

        # Record sync status (extended with observed status badge for debugging/drift checks).
        if sync_status is not None and not dry_run:
            status_data = sync_status.model_dump(mode="json")
            status_data["status_badge_text"] = website_data.status_badge_text
            status_data["warnings"] = warnings
            _save_sync_status(problem_id, status_data)

        return CLIOutput.ok(
            command="erdos sync website",
            data={
                "problem_id": problem_id,
                "updated": updated,
                "latex_saved": latex_saved,
                "cached": cached,
                "warnings": warnings,
                "title": merged.title,
                "status": merged.status.value,
            },
        )

    except WebsiteFetchError as e:
        code = ExitCode.NETWORK_ERROR if e.status_code != 404 else ExitCode.NOT_FOUND
        return CLIOutput.err(
            command="erdos sync website",
            error_type="FetchError",
            message=str(e),
            code=code,
        )
    except WebsiteParseError as e:
        return CLIOutput.err(
            command="erdos sync website",
            error_type="ParseError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in sync website")
        return CLIOutput.err(
            command="erdos sync website",
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
    title = data.get("title", "Unknown")
    updated = data.get("updated", False)
    latex_saved = data.get("latex_saved", False)
    cached = data.get("cached", False)
    warnings = data.get("warnings", [])
    status = data.get("status", "unknown")

    status_icon = "\u2713" if updated else "-"
    source_text = "(from cache)" if cached else "(from network)"

    lines = [
        f"[bold]Problem {problem_id}:[/bold] {title}",
        f"Status: {status}",
        f"Updated: {'Yes' if updated else 'No (no changes)'} {source_text}",
    ]

    if latex_saved:
        lines.append("LaTeX: Saved to data/latex/")

    if warnings:
        lines.append("")
        lines.append("[yellow]Warnings:[/yellow]")
        for w in warnings:
            lines.append(f"  - {w}")

    panel = Panel(
        "\n".join(lines),
        title=f"{status_icon} Sync Result",
        expand=False,
    )
    console.print(panel)


# =============================================================================
# CLI Command
# =============================================================================


def website(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(
            help="Problem ID to sync from erdosproblems.com",
            min=1,
        ),
    ],
    latex: Annotated[
        bool,
        typer.Option(
            "--latex",
            help="Also fetch and save raw LaTeX source to data/latex/<id>.tex",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would change without writing to disk",
        ),
    ] = False,
) -> None:
    """
    Fetch structured data from erdosproblems.com and update local dataset.

    Extracts title, statement, tags, and references from the website.
    Updates data/problems_enriched.yaml with the merged data.

    Example:
        erdos sync website 6
        erdos sync website 6 --latex
    """
    with measure_time_ms() as duration:
        result = sync_website_problem(
            problem_id,
            fetch_latex=latex,
            dry_run=dry_run,
        )

    result.duration_ms = duration[0]
    exit_with_result(ctx, result, print_human=_print_human)
