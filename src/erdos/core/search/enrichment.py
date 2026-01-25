"""Result enrichment helpers for search."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


logger = logging.getLogger(__name__)


def enrich_result(
    result: dict[str, object],
    repo: ProblemRepository | None,
    problem_id: int | None,
) -> dict[str, object]:
    """Add problem title to search result if available."""
    if repo is not None and problem_id is not None:
        try:
            problem = repo.get_by_id(problem_id)
            if problem:
                result["title"] = problem.title
        except Exception:  # enrichment is best-effort; never fail search
            logger.debug(
                "Failed to enrich result for problem %s",
                problem_id,
                exc_info=True,
            )
    return result
