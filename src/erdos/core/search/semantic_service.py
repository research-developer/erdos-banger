"""Semantic and hybrid search services."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.search.db import SearchIndexError
from erdos.core.search.embeddings_service import get_embedding_model
from erdos.core.search.facade import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol
    from erdos.core.search.options import SearchOptions


def search_semantic(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute semantic search.

    Args:
        options: Search options
        index: Search index
        repo: Problem repository for enrichment

    Returns:
        CLIOutput with semantic search results
    """
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Semantic search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = get_embedding_model(options.embedding_model)
    if err:
        return err
    if embedder is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        results = index.search_semantic(
            options.query,
            embedder,
            limit=options.limit,
            problem_id=options.problem_id,
        )

        # Enrich results with problem titles
        enriched_results = []
        for r in results:
            problem = None
            if r.problem_id is not None:
                with contextlib.suppress(Exception):
                    problem = repo.get_by_id(r.problem_id)
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "semantic_score": r.semantic_score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": options.query,
                "mode": "semantic",
                "count": len(enriched_results),
                "results": enriched_results,
                "embedding_model": options.embedding_model,
            },
        )
    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )


def search_hybrid(
    options: SearchOptions,
    *,
    index: SearchIndexProtocol,
    repo: ProblemRepository,
) -> CLIOutput:
    """Execute hybrid BM25 + semantic search.

    Args:
        options: Search options (uses alpha for weighting)
        index: Search index
        repo: Problem repository for enrichment

    Returns:
        CLIOutput with hybrid search results
    """
    if not isinstance(index, SearchIndex):
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Hybrid search requires SearchIndex instance",
            code=ExitCode.CONFIG_ERROR,
        )

    embedder, err = get_embedding_model(options.embedding_model)
    if err:
        return err
    if embedder is None:
        return CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        results = index.search_hybrid(
            options.query,
            embedder,
            limit=options.limit,
            alpha=options.alpha,
            problem_id=options.problem_id,
        )

        # Enrich results with problem titles
        enriched_results = []
        for r in results:
            problem = None
            if r.problem_id is not None:
                with contextlib.suppress(Exception):
                    problem = repo.get_by_id(r.problem_id)
            enriched_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "snippet": r.snippet,
                    "score": r.bm25_score,
                    "semantic_score": r.semantic_score,
                    "hybrid_score": r.hybrid_score,
                    "source_type": r.source_type.value,
                    "problem_id": r.problem_id,
                    "title": problem.title if problem else None,
                    "reference_doi": r.reference_doi,
                }
            )

        return CLIOutput.ok(
            command="erdos search",
            data={
                "query": options.query,
                "mode": "hybrid",
                "alpha": options.alpha,
                "count": len(enriched_results),
                "results": enriched_results,
                "embedding_model": options.embedding_model,
            },
        )
    except SearchIndexError as e:
        return CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )
