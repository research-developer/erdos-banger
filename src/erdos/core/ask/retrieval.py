"""Retrieval logic for RAG Q&A."""

from pathlib import Path

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import ChunkSource, ProblemRecord
from erdos.core.ports import SearchIndexReadPort
from erdos.core.research.paths import get_problem_dir
from erdos.core.search.bm25 import safe_fts5_query
from erdos.core.search.types import SearchResult


def _try_load_synthesis(problem_id: int, *, repo_root: Path | None) -> str | None:
    path = get_problem_dir(repo_root, problem_id) / "SYNTHESIS.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def perform_retrieval(
    index: SearchIndexReadPort,
    problem: ProblemRecord,
    question: str,
    limit: int,
) -> tuple[list[SearchResult], str | None]:
    """
    Retrieve relevant text chunks for a question about a problem.

    Args:
        index: The search index
        problem: The problem record
        question: User's question
        limit: Maximum number of chunks to retrieve

    Returns:
        List of search results, ordered by relevance
    """
    # Build a safe FTS5 query. Using an exact phrase match for the full question is
    # too strict (it often returns zero results). Instead, extract tokens from the
    # problem title + question and OR them together.
    #
    # NOTE: We explicitly disable advanced syntax preservation here because this
    # query is programmatically constructed from free text (question). Users may
    # include stray quotes/operators which should not be treated as FTS5 syntax.
    haystack = f"{problem.title} {question}"
    query = safe_fts5_query(haystack, allow_advanced_syntax=False)
    if query == '""':
        return ([], None)

    # Search with problem_id filter to bias towards this problem
    results = index.search(
        query,
        limit=limit,
        problem_id=problem.id,
    )

    return (results, query)


def fallback_sources(problem: ProblemRecord, *, limit: int) -> list[SearchResult]:
    """Fallback retrieval when the FTS index has no data yet."""
    return fallback_sources_with_research(problem, limit=limit, repo_root=None)


def fallback_sources_with_research(
    problem: ProblemRecord, *, limit: int, repo_root: Path | None
) -> list[SearchResult]:
    """Fallback retrieval including research synthesis when present."""
    sources: list[SearchResult] = []

    # Always include synthesis first when present.
    synthesis = _try_load_synthesis(problem.id, repo_root=repo_root)
    if synthesis is not None and len(sources) < limit:
        sources.append(
            SearchResult(
                chunk_id=f"research_{problem.id}_synthesis",
                text=synthesis,
                snippet=synthesis[:PREVIEW_LENGTH] + "..."
                if len(synthesis) > PREVIEW_LENGTH
                else synthesis,
                score=1.0,
                source_type=ChunkSource.RESEARCH_SYNTHESIS,
                problem_id=problem.id,
                reference_doi=None,
            )
        )

    # Always include the statement first (matches TextChunk.from_problem conventions).
    statement = problem.statement
    sources.append(
        SearchResult(
            chunk_id=f"problem_{problem.id}_statement",
            text=statement,
            snippet=statement[:PREVIEW_LENGTH] + "..."
            if len(statement) > PREVIEW_LENGTH
            else statement,
            score=1.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=problem.id,
            reference_doi=None,
        )
    )

    # Include notes if present and within limit.
    if problem.notes and len(sources) < limit:
        notes = problem.notes
        sources.append(
            SearchResult(
                chunk_id=f"problem_{problem.id}_notes",
                text=notes,
                snippet=notes[:PREVIEW_LENGTH] + "..."
                if len(notes) > PREVIEW_LENGTH
                else notes,
                score=0.5,
                source_type=ChunkSource.PROBLEM_NOTES,
                problem_id=problem.id,
                reference_doi=None,
            )
        )

    return sources[: max(limit, 0)]


def retrieve_sources(
    *,
    index: SearchIndexReadPort,
    problem: ProblemRecord,
    question: str,
    limit: int,
    repo_root: Path | None = None,
) -> tuple[list[SearchResult], bool, str | None]:
    """
    Retrieve sources for a question, with fallback.

    Args:
        index: Search index
        problem: Problem record
        question: User's question
        limit: Maximum sources to retrieve

    Returns:
        Tuple of (sources, used_fts, query) where used_fts indicates if FTS was used
        and query is the exact FTS query string (or None if not used).
    """
    # If index is empty, use fallback sources
    if index.chunk_count() == 0:
        sources = fallback_sources_with_research(
            problem, limit=limit, repo_root=repo_root
        )
        return sources, False, None

    # Otherwise, combine fallback (statement/notes) with retrieved chunks
    baseline = fallback_sources_with_research(problem, limit=limit, repo_root=repo_root)
    retrieved, query = perform_retrieval(
        index=index,
        problem=problem,
        question=question,
        limit=limit,
    )
    used_fts = query is not None

    # Deduplicate by chunk_id, preferring baseline order first
    combined: list[SearchResult] = []
    seen_ids: set[str] = set()
    for source in [*baseline, *retrieved]:
        if source.chunk_id in seen_ids:
            continue
        seen_ids.add(source.chunk_id)
        combined.append(source)
        if len(combined) >= limit:
            break

    return combined, used_fts, query
