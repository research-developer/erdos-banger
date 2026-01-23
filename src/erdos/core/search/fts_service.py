"""FTS5-based full-text search service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.search.db import SearchIndexError
from erdos.core.search.enrichment import enrich_result


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexReadPort


logger = logging.getLogger(__name__)


def search_fts(
    query: str,
    *,
    index: SearchIndexReadPort,
    repo: ProblemRepository | None = None,
    limit: int = 10,
    problem_id: int | None = None,
) -> CLIOutput | None:
    """Search using FTS5 index (preferred).

    Returns None if index is empty (caller should fall back to basic search).

    Args:
        query: Search query
        index: Search index read port (only read operations needed)
        repo: Optional problem repository for enrichment
        limit: Maximum results
        problem_id: Optional filter to specific problem

    Returns:
        CLIOutput with results, error, or None if index is empty
    """
    try:
        # Guard against empty query
        if not query.strip():
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Query must not be empty",
                code=ExitCode.USAGE_ERROR,
            )

        if limit <= 0:
            return CLIOutput.err(
                command="erdos search",
                error_type="UsageError",
                message="Limit must be greater than 0",
                code=ExitCode.USAGE_ERROR,
            )

        # Return None to signal fallback needed if index is empty
        if index.problem_count() == 0:
            return None

        results = index.search(query, limit=limit, problem_id=problem_id)

        enriched_results = []
        for r in results:
            result_dict = {
                "chunk_id": r.chunk_id,
                "snippet": r.snippet,
                "score": r.score,
                "source_type": r.source_type.value,
                "problem_id": r.problem_id,
                "title": None,
                "reference_doi": r.reference_doi,
            }
            enriched = enrich_result(result_dict, repo, r.problem_id)
            enriched_results.append(enriched)

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(enriched_results),
                "results": enriched_results,
                "use_fts": True,
            },
        )

    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )
    except Exception as e:
        logger.exception("Unexpected error in FTS search")
        return CLIOutput.err(
            command="erdos search",
            error_type="Error",
            message=str(e),
            code=ExitCode.ERROR,
        )
