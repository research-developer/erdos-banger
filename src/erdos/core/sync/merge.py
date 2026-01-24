"""Pure merge logic for combining problem data sources (SPEC-035).

This module implements the field precedence rules defined in SPEC-035:

| Field       | Source     | Merge rule                                        |
|-------------|------------|---------------------------------------------------|
| id          | Input      | Must match requested problem id                   |
| title       | Website    | Overwrite only on successful parse                |
| statement   | Website    | Overwrite only on successful parse; never empty   |
| references  | Website    | Overwrite only on successful parse                |
| status      | Submodule  | Overwrite on successful submodule parse           |
| prize       | Submodule  | Overwrite on successful submodule parse           |
| tags        | Submodule  | Overwrite on successful submodule parse           |
| formalized  | Submodule  | Overwrite on successful submodule parse           |
| oeis_ids    | Submodule  | Overwrite on successful submodule parse           |
| notes       | Local      | Preserve existing; only fill when missing         |

All merge functions are pure (no I/O, no side effects) and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry


if TYPE_CHECKING:
    from erdos.core.sync.models import SubmoduleProblemData, WebsiteProblemData


# =============================================================================
# Merge context dataclass (reduces parameter passing)
# =============================================================================


@dataclass
class _MergeContext:
    """Internal context for merge operations."""

    problem_id: int
    submodule: SubmoduleProblemData | None
    website: WebsiteProblemData | None
    existing: ProblemRecord | None
    overwrite_notes: bool


# =============================================================================
# Field resolution helpers (reduce branches in main function)
# =============================================================================


def _resolve_title(ctx: _MergeContext) -> str | None:
    """Resolve title field (Website authoritative)."""
    if ctx.website is not None and ctx.website.title:
        return ctx.website.title
    if ctx.existing is not None:
        return ctx.existing.title
    return None


def _resolve_statement(ctx: _MergeContext) -> str | None:
    """Resolve statement field (Website authoritative, never empty)."""
    if ctx.website is not None and ctx.website.statement:
        return ctx.website.statement
    if ctx.existing is not None:
        return ctx.existing.statement
    return None


def _resolve_status(ctx: _MergeContext) -> ProblemStatus:
    """Resolve status field (Submodule authoritative)."""
    if ctx.submodule is not None:
        return ProblemStatus.from_string(ctx.submodule.status)
    if ctx.existing is not None:
        return ctx.existing.status
    return ProblemStatus.OPEN


def _resolve_prize(ctx: _MergeContext) -> int:
    """Resolve prize field (Submodule authoritative)."""
    if ctx.submodule is not None:
        return ctx.submodule.prize
    if ctx.existing is not None:
        return ctx.existing.prize
    return 0


def _resolve_tags(ctx: _MergeContext) -> list[str]:
    """Resolve tags field (Submodule primary, fallback to existing)."""
    if ctx.submodule is not None and ctx.submodule.tags:
        return list(ctx.submodule.tags)
    if ctx.existing is not None:
        return list(ctx.existing.tags)
    return []


def _website_ref_to_entry(ref_dict: dict[str, Any]) -> ReferenceEntry:
    """Convert a WebsiteReferenceData dict to ReferenceEntry."""
    return ReferenceEntry(
        key=ref_dict.get("key", ""),
        citation=ref_dict.get("citation"),
        doi=ref_dict.get("doi"),
        arxiv_id=ref_dict.get("arxiv_id"),
        url=ref_dict.get("url"),
    )


def _resolve_references(ctx: _MergeContext) -> list[ReferenceEntry]:
    """Resolve references field (Website authoritative)."""
    if ctx.website is not None:
        return [
            _website_ref_to_entry(ref.model_dump()) for ref in ctx.website.references
        ]
    if ctx.existing is not None:
        return list(ctx.existing.references)
    return []


def _resolve_oeis_ids(ctx: _MergeContext) -> list[str]:
    """Resolve oeis_ids field (Submodule authoritative)."""
    if ctx.submodule is not None:
        return list(ctx.submodule.oeis_ids)
    if ctx.existing is not None:
        return list(ctx.existing.oeis_ids)
    return []


def _resolve_formalized(ctx: _MergeContext) -> bool:
    """Resolve formalized field (Submodule authoritative)."""
    if ctx.submodule is not None:
        return ctx.submodule.formalized
    if ctx.existing is not None:
        return ctx.existing.formalized
    return False


def _resolve_notes(ctx: _MergeContext) -> str | None:
    """Resolve notes field (Local preserved, optionally cleared)."""
    if ctx.overwrite_notes:
        return None
    if ctx.existing is not None:
        return ctx.existing.notes
    return None


def _validate_problem_ids(ctx: _MergeContext) -> None:
    """Validate that all source problem_ids match the requested id."""
    if ctx.submodule is not None and ctx.submodule.problem_id != ctx.problem_id:
        raise ValueError(
            f"Submodule problem_id mismatch: expected {ctx.problem_id}, "
            f"got {ctx.submodule.problem_id}"
        )
    if ctx.website is not None and ctx.website.problem_id != ctx.problem_id:
        raise ValueError(
            f"Website problem_id mismatch: expected {ctx.problem_id}, "
            f"got {ctx.website.problem_id}"
        )


# =============================================================================
# Main merge functions
# =============================================================================


def merge_problem_data(
    problem_id: int,
    *,
    submodule: SubmoduleProblemData | None = None,
    website: WebsiteProblemData | None = None,
    existing: ProblemRecord | None = None,
    overwrite_notes: bool = False,
) -> ProblemRecord | None:
    """
    Merge data from multiple sources into a ProblemRecord.

    This is a **pure function** with deterministic behavior:
    - Field precedence follows SPEC-035 rules
    - Missing sources are gracefully handled
    - Returns None only if no data is available for required fields

    Args:
        problem_id: The problem ID to create/update
        submodule: Data from teorth/erdosproblems submodule
        website: Data from erdosproblems.com website
        existing: Existing ProblemRecord (for preserving notes)
        overwrite_notes: If True, overwrite existing notes

    Returns:
        Merged ProblemRecord, or None if required fields are unavailable
    """
    ctx = _MergeContext(
        problem_id=problem_id,
        submodule=submodule,
        website=website,
        existing=existing,
        overwrite_notes=overwrite_notes,
    )

    _validate_problem_ids(ctx)

    title = _resolve_title(ctx)
    statement = _resolve_statement(ctx)

    # Required fields check
    if not title or not statement:
        return None

    return ProblemRecord(
        id=problem_id,
        title=title,
        statement=statement,
        status=_resolve_status(ctx),
        prize=_resolve_prize(ctx),
        tags=_resolve_tags(ctx),
        references=_resolve_references(ctx),
        oeis_ids=_resolve_oeis_ids(ctx),
        notes=_resolve_notes(ctx),
        formalized=_resolve_formalized(ctx),
    )


def merge_all_problems(
    submodule_data: dict[int, SubmoduleProblemData],
    website_data: dict[int, WebsiteProblemData],
    existing_problems: dict[int, ProblemRecord] | None = None,
    *,
    overwrite_notes: bool = False,
) -> list[ProblemRecord]:
    """
    Merge data for all problems from multiple sources.

    This is a batch version of merge_problem_data that handles multiple problems
    with deterministic ordering (ascending by problem_id).

    Args:
        submodule_data: Dict of problem_id -> SubmoduleProblemData
        website_data: Dict of problem_id -> WebsiteProblemData
        existing_problems: Dict of problem_id -> existing ProblemRecord
        overwrite_notes: If True, overwrite existing notes

    Returns:
        List of merged ProblemRecords, sorted by id (ascending)
    """
    if existing_problems is None:
        existing_problems = {}

    all_ids = (
        set(submodule_data.keys())
        | set(website_data.keys())
        | set(existing_problems.keys())
    )

    results: list[ProblemRecord] = []
    for pid in sorted(all_ids):
        merged = merge_problem_data(
            pid,
            submodule=submodule_data.get(pid),
            website=website_data.get(pid),
            existing=existing_problems.get(pid),
            overwrite_notes=overwrite_notes,
        )
        if merged is not None:
            results.append(merged)

    return results
