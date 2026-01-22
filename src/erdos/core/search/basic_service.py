"""Basic substring search service (fallback when no index)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput, ProblemRecord


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository


logger = logging.getLogger(__name__)


def search_basic(
    query: str,
    repo: ProblemRepository,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput:
    """Fallback: basic substring search (no ranking).

    Args:
        query: Search query
        repo: Problem repository
        limit: Maximum results
        problem_id: Optional filter to specific problem

    Returns:
        CLIOutput with results or error
    """
    try:
        q = query.lower().strip()
        if not q:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        # If problem_id specified, search only that problem
        if problem_id is not None:
            problem = repo.get_by_id(problem_id)
            if problem is None:
                return CLIOutput.err(
                    command="erdos search",
                    error_type="NotFound",
                    message=f"Problem {problem_id} not found",
                    code=ExitCode.NOT_FOUND,
                )
            candidates = [problem]
        else:
            candidates = repo.load_all()

        matches: list[ProblemRecord] = []
        for problem in candidates:
            if q in problem.title.lower() or q in problem.statement.lower():
                matches.append(problem)

        matches = sorted(matches, key=lambda p: p.id)[:limit]

        results = [
            {
                "problem_id": p.id,
                "title": p.title,
                "snippet": p.statement[:PREVIEW_LENGTH] + "..."
                if len(p.statement) > PREVIEW_LENGTH
                else p.statement,
                "score": None,
                "source_type": "problem_statement",
            }
            for p in matches
        ]

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(results),
                "results": results,
                "use_fts": False,
            },
        )
    except Exception as e:
        logger.exception("Unexpected error in basic search")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )
