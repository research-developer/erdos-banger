"""Search service: orchestrates search operations for Erdős problems.

This module is a thin orchestrator that coordinates the specialized search
services. The CLI adapter (commands/search.py) calls these functions and
handles Typer/Rich presentation.

Re-exports from submodules for backward compatibility:
- SearchMode, SearchOptions from options
- search_fts from fts_service
- search_basic from basic_service
- get_embedding_model, build_embeddings from embeddings_service
- build_search_index from indexing_service
- search_semantic, search_hybrid from semantic_service
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput

# Re-export from submodules for backward compatibility
from erdos.core.search.basic_service import search_basic
from erdos.core.search.embeddings_service import build_embeddings, get_embedding_model
from erdos.core.search.fts_service import search_fts
from erdos.core.search.indexing_service import build_search_index
from erdos.core.search.options import SearchMode, SearchOptions
from erdos.core.search.semantic_service import search_hybrid, search_semantic


if TYPE_CHECKING:
    from erdos.core.ports import (
        ProblemRepository,
        SearchIndexProtocol,
        SearchIndexReadPort,
    )


# Re-export symbols for backward compatibility
__all__ = [
    "SearchMode",
    "SearchOptions",
    "build_embeddings",
    "build_search_index",
    "execute_search",
    "get_embedding_model",
    "search_basic",
    "search_fts",
    "search_hybrid",
    "search_semantic",
    "search_with_fallback",
]


def search_with_fallback(
    options: SearchOptions,
    *,
    index: SearchIndexReadPort | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute FTS search with fallback to basic substring search.

    Args:
        options: Search options
        index: Search index read port (may be None if unavailable)
        repo: Problem repository

    Returns:
        CLIOutput with search results
    """
    if index is None:
        result = search_basic(options.query, repo, options.limit, options.problem_id)
        if result.success and result.data:
            result.data["mode"] = "basic"
        return result

    fts_result = search_fts(
        options.query,
        index=index,
        repo=repo,
        limit=options.limit,
        problem_id=options.problem_id,
    )

    # None means index is empty - fall back to basic search
    if fts_result is None:
        result = search_basic(options.query, repo, options.limit, options.problem_id)
        if result.success and result.data:
            result.data["mode"] = "basic"
            result.data["fallback_reason"] = "index_empty"
        return result

    # Update mode for display
    if fts_result.success and fts_result.data:
        fts_result.data["mode"] = "bm25"

    return fts_result


def execute_search(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol | None,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute search based on mode.

    This is the main entry point for search operations.

    Args:
        options: Search options including mode
        index: Search index (may be None)
        repo: Problem repository

    Returns:
        CLIOutput with search results
    """
    if options.mode == SearchMode.SEMANTIC:
        if index is None:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexError",
                message="Search index is unavailable",
                code=ExitCode.ERROR,
            )
        return search_semantic(options, index=index, repo=repo)

    if options.mode == SearchMode.HYBRID:
        if index is None:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexError",
                message="Search index is unavailable",
                code=ExitCode.ERROR,
            )
        return search_hybrid(options, index=index, repo=repo)

    # BM25 search (default) with fallback
    return search_with_fallback(options, index=index, repo=repo)
