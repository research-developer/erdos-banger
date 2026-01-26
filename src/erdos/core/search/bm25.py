"""BM25/FTS5 search operations.

This module handles FTS5 full-text search with BM25 ranking.
Separated from indexing and embedding operations per SRP.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from erdos.core.constants import DEFAULT_SEARCH_LIMIT, MAX_QUERY_TERMS
from erdos.core.models import ChunkSource
from erdos.core.search.types import SearchResult


if TYPE_CHECKING:
    from erdos.core.search.db import DatabaseManager


def safe_fts5_query(query: str) -> str:
    """Escape a query for safe FTS5 matching while preserving useful syntax.

    FTS5 has special syntax that can cause errors when passed raw (e.g., hyphens
    interpreted as NOT operator). This function preserves useful FTS5 features
    while escaping dangerous constructs.

    Preserved features:
    - Prefix matching: prim* matches primes, prime, etc.
    - Phrase matching: "arithmetic progressions" matches exact phrase
    - Boolean operators: word1 OR word2, word1 AND word2

    Escaped:
    - Hyphens in words (sum-free -> "sum" OR "free")
    - Standalone special chars

    Args:
        query: Raw user query

    Returns:
        Safe FTS5 query
    """
    # Check if query uses explicit FTS5 syntax (phrases, prefix, operators)
    has_phrase = '"' in query
    has_prefix = "*" in query
    has_boolean = bool(re.search(r"\b(AND|OR|NOT)\b", query))

    # If using advanced syntax, do minimal escaping to preserve intent
    if has_phrase or has_prefix or has_boolean:
        # Replace hyphens with spaces (to avoid NOT interpretation)
        # but preserve the rest of the query structure
        safe_query = re.sub(r"(?<=[a-zA-Z])-(?=[a-zA-Z])", " ", query)
        return safe_query

    # For plain queries, tokenize and quote for maximum safety
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    if not tokens:
        return '""'  # Empty match returns no results gracefully
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    quoted = [f'"{t}"' for t in unique[:MAX_QUERY_TERMS]]
    return " OR ".join(quoted)


class BM25Search:
    """Handles BM25/FTS5 search operations (read path).

    Responsibilities:
    - Full-text search with FTS5
    - BM25 ranking and snippet generation
    - Filtering by problem ID and source type
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize BM25 search with database manager.

        Args:
            db: Database manager instance
        """
        self._db = db

    def search(
        self,
        query: str,
        *,
        limit: int = DEFAULT_SEARCH_LIMIT,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]:
        """Search the index using BM25.

        Args:
            query: Search query (supports FTS5 syntax)
            limit: Maximum results to return
            problem_id: Optionally filter to a specific problem
            source_types: Optionally filter by source types

        Returns:
            List of SearchResult objects, sorted by relevance
        """
        if not query.strip():
            return []

        # Escape the query for FTS5 safety (handles hyphens, operators, etc.)
        escaped_query = safe_fts5_query(query)
        if escaped_query == '""':
            return []  # No valid tokens

        # Build query with filters
        sql = """
            SELECT
                c.id,
                c.text,
                snippet(chunks_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(chunks_fts) as score,
                c.source_type,
                c.problem_id,
                c.reference_doi
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c._rowid
            WHERE chunks_fts MATCH ?
        """
        params: list[str | int] = [escaped_query]

        if problem_id is not None:
            sql += " AND c.problem_id = ?"
            params.append(problem_id)

        if source_types:
            placeholders = ",".join("?" * len(source_types))
            sql += f" AND c.source_type IN ({placeholders})"
            params.extend(st.value for st in source_types)

        sql += " ORDER BY score LIMIT ?"
        params.append(limit)

        results = []
        with self._db.connect() as conn:
            cursor = conn.execute(sql, params)
            for row in cursor:
                results.append(
                    SearchResult(
                        chunk_id=row["id"],
                        text=row["text"],
                        snippet=row["snippet"],
                        score=abs(row["score"]),  # BM25 returns negative scores
                        source_type=ChunkSource(row["source_type"]),
                        problem_id=row["problem_id"],
                        reference_doi=row["reference_doi"],
                    )
                )

        return results
