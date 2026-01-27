"""Core logic for adding reference identifiers to the local enriched dataset."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erdos.core.sync.dataset import load_enriched_problems, save_enriched_problems


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.models import ProblemRecord, ReferenceEntry


def _dedupe_key(key: str, existing_keys: set[str]) -> str:
    if key not in existing_keys:
        return key
    suffix = 2
    while f"{key}-{suffix}" in existing_keys:
        suffix += 1
    return f"{key}-{suffix}"


def _normalize_identifier(value: str) -> str:
    return value.strip()


def _normalize_doi(value: str) -> str:
    return value.strip().lower()


def add_reference_to_problem(
    *,
    problem_id: int,
    reference: ReferenceEntry,
    dataset_path: Path,
) -> tuple[ProblemRecord | None, bool, ReferenceEntry | None, str | None]:
    """Add a ReferenceEntry to the local enriched dataset.

    Returns:
        (updated_problem, updated, stored_reference, error_message)
    """
    try:
        problems = load_enriched_problems(dataset_path)
        problem = problems.get(problem_id)
        if problem is None:
            # Not an I/O failure; callers should treat this as a normal NotFound case.
            return None, False, None, None

        existing_keys = {r.key for r in problem.references}
        existing_dois: dict[str, ReferenceEntry] = {}
        existing_arxiv: dict[str, ReferenceEntry] = {}
        existing_urls: dict[str, ReferenceEntry] = {}
        for ref in problem.references:
            if ref.doi is not None:
                existing_dois[_normalize_doi(ref.doi)] = ref
            if ref.arxiv_id is not None:
                existing_arxiv[_normalize_identifier(ref.arxiv_id)] = ref
            if ref.url is not None:
                existing_urls[_normalize_identifier(ref.url)] = ref

        doi = _normalize_doi(reference.doi) if reference.doi else None
        arxiv_id = (
            _normalize_identifier(reference.arxiv_id) if reference.arxiv_id else None
        )
        url = _normalize_identifier(reference.url) if reference.url else None

        if doi is not None and doi in existing_dois:
            return problem, False, existing_dois[doi], None
        if arxiv_id is not None and arxiv_id in existing_arxiv:
            return problem, False, existing_arxiv[arxiv_id], None
        if url is not None and url in existing_urls:
            return problem, False, existing_urls[url], None

        key = _dedupe_key(reference.key, existing_keys)
        ref = (
            reference
            if key == reference.key
            else reference.model_copy(update={"key": key})
        )

        updated_refs = [*problem.references, ref]
        updated_problem = problem.model_copy(update={"references": updated_refs})
        problems[problem_id] = updated_problem
        save_enriched_problems(dataset_path, problems)
        return updated_problem, True, ref, None
    except Exception as e:
        logger.exception("Failed to update dataset references")
        return None, False, None, str(e)
