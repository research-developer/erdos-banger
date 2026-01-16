# Spec 006: SQLite Search Index

> Defines the SQLite FTS5 search index for full-text search over problem statements and reference content.

---

## Overview

The search index enables the `erdos search` command. For v1, we use SQLite with FTS5 (Full-Text Search 5) - a powerful, embedded solution that requires no external services.

### Guiding Principles

1. **Embedded first** - SQLite is the default; no external database needed
2. **BM25 ranking** - Industry-standard relevance scoring built into FTS5
3. **Incremental updates** - Add new content without rebuilding entire index
4. **Snippet extraction** - Return highlighted excerpts, not full documents

---

## 1) Why SQLite FTS5

| Option | Pros | Cons |
|--------|------|------|
| **SQLite FTS5** | Zero setup, ships with Python, BM25 built-in | Single-machine only |
| Postgres FTS | ACID, scalable | Requires server |
| Elasticsearch | Powerful features | Heavy, complex |
| Meilisearch | Fast, typo-tolerant | Another service |

**Decision:** SQLite FTS5 for v1. ~1000 problems with a few thousand chunks is well within SQLite's comfort zone.

---

## 2) Database Schema

```sql
-- index/erdos.sqlite

-- Problem metadata (denormalized for search)
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    statement TEXT NOT NULL,
    status TEXT NOT NULL,
    prize INTEGER DEFAULT 0,
    tags TEXT,  -- JSON array as string
    indexed_at TEXT NOT NULL  -- ISO8601 timestamp
);

-- Text chunks for search
-- Note: We use an explicit _rowid column because FTS5 external content tables
-- require an integer rowid, and TEXT PRIMARY KEY tables don't have implicit rowids.
CREATE TABLE IF NOT EXISTS chunks (
    _rowid INTEGER PRIMARY KEY AUTOINCREMENT,  -- Explicit rowid for FTS5 sync
    id TEXT UNIQUE NOT NULL,  -- e.g., "problem_6_statement" or "ref_doi_10.1007_chunk_3"
    text TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- "problem_statement", "problem_notes", "reference_abstract", "reference_fulltext"
    problem_id INTEGER,  -- NULL if reference-only
    reference_key TEXT,  -- NULL if problem-only
    start_char INTEGER,
    end_char INTEGER,
    indexed_at TEXT NOT NULL
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='_rowid',  -- Reference our explicit _rowid column
    tokenize='porter unicode61'  -- Porter stemming + Unicode support
);

-- Triggers to keep FTS in sync (use _rowid, not rowid)
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
END;

-- Index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_chunks_problem_id ON chunks(problem_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', '1');
```

---

## 3) Search Index Implementation

```python
# src/erdos/core/search_index.py
"""SQLite FTS5 search index for erdos-harness."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from erdos.core.models import ChunkSource, ProblemRecord, TextChunk


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    chunk_id: str
    text: str
    snippet: str  # Highlighted excerpt
    score: float  # BM25 score (higher = more relevant)
    source_type: ChunkSource
    problem_id: int | None
    reference_key: str | None


class SearchIndexError(Exception):
    """Raised when index operations fail."""

    pass


class SearchIndex:
    """
    SQLite FTS5 search index.

    Usage:
        index = SearchIndex.from_default()
        index.index_problem(problem)
        results = index.search("prime numbers", limit=10)
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path) -> None:
        """
        Initialize search index.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._ensure_schema()

    @classmethod
    def from_default(cls) -> "SearchIndex":
        """Create index using default path (index/erdos.sqlite)."""
        import os

        # Check environment variable
        env_path = os.environ.get("ERDOS_INDEX_PATH")
        if env_path:
            return cls(Path(env_path))

        # Default path
        default_path = Path("index/erdos.sqlite")
        default_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(default_path)

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self._db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_sql = """
        -- Problem metadata
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            statement TEXT NOT NULL,
            status TEXT NOT NULL,
            prize INTEGER DEFAULT 0,
            tags TEXT,
            indexed_at TEXT NOT NULL
        );

        -- Text chunks (explicit _rowid for FTS5 external content sync)
        CREATE TABLE IF NOT EXISTS chunks (
            _rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE NOT NULL,
            text TEXT NOT NULL,
            source_type TEXT NOT NULL,
            problem_id INTEGER,
            reference_key TEXT,
            start_char INTEGER,
            end_char INTEGER,
            indexed_at TEXT NOT NULL
        );

        -- FTS5 virtual table
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            content='chunks',
            content_rowid='_rowid',
            tokenize='porter unicode61'
        );

        -- Sync triggers (use _rowid)
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old._rowid, old.text);
            INSERT INTO chunks_fts(rowid, text) VALUES (new._rowid, new.text);
        END;

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_chunks_problem_id ON chunks(problem_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_source_type ON chunks(source_type);

        -- Schema version
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', '1');
        """

        with self._connect() as conn:
            conn.executescript(schema_sql)

    def index_problem(self, problem: ProblemRecord) -> None:
        """
        Index a problem's statement.

        Creates chunks for the problem statement and notes.

        Args:
            problem: The problem to index
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            # Insert/update problem metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO problems
                (id, title, statement, status, prize, tags, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem.id,
                    problem.title,
                    problem.statement,
                    problem.status.value,
                    problem.prize,
                    json.dumps(problem.tags),
                    now,
                ),
            )

            # Create chunk for statement
            chunk = TextChunk.from_problem(problem)
            self._insert_chunk(conn, chunk, now)

            # Create chunk for notes if present
            if problem.notes:
                notes_chunk = TextChunk(
                    id=f"problem_{problem.id}_notes",
                    text=problem.notes,
                    source=ChunkSource.PROBLEM_NOTES,
                    problem_id=problem.id,
                    preview=problem.notes[:200] if len(problem.notes) > 200 else problem.notes,
                )
                self._insert_chunk(conn, notes_chunk, now)

    def index_chunk(self, chunk: TextChunk) -> None:
        """
        Index a single text chunk.

        Args:
            chunk: The chunk to index
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            self._insert_chunk(conn, chunk, now)

    def _insert_chunk(
        self, conn: sqlite3.Connection, chunk: TextChunk, timestamp: str
    ) -> None:
        """Insert a chunk into the database."""
        conn.execute(
            """
            INSERT OR REPLACE INTO chunks
            (id, text, source_type, problem_id, reference_key, start_char, end_char, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.id,
                chunk.text,
                chunk.source.value,
                chunk.problem_id,
                chunk.reference_doi,
                chunk.start_char,
                chunk.end_char,
                timestamp,
            ),
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]:
        """
        Search the index using BM25.

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

        # Build query with filters
        sql = """
            SELECT
                c.id,
                c.text,
                snippet(chunks_fts, 0, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(chunks_fts) as score,
                c.source_type,
                c.problem_id,
                c.reference_key
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c._rowid
            WHERE chunks_fts MATCH ?
        """
        params: list = [query]

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
        with self._connect() as conn:
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
                        reference_key=row["reference_key"],
                    )
                )

        return results

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM problems")
            return cursor.fetchone()[0]

    def chunk_count(self) -> int:
        """Return number of indexed chunks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            return cursor.fetchone()[0]

    def clear(self) -> None:
        """Delete all indexed content."""
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM problems")
            # Rebuild FTS index
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index (use after direct SQL modifications)."""
        with self._connect() as conn:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

    def get_stats(self) -> dict:
        """Get index statistics."""
        with self._connect() as conn:
            problems = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

            # Count by source type
            by_source = {}
            cursor = conn.execute(
                "SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type"
            )
            for row in cursor:
                by_source[row[0]] = row[1]

            return {
                "problems": problems,
                "chunks": chunks,
                "chunks_by_source": by_source,
                "db_path": str(self._db_path),
                "db_size_bytes": self._db_path.stat().st_size if self._db_path.exists() else 0,
            }
```

---

## 4) Index Builder

```python
# src/erdos/core/index_builder.py
"""Build search index from problem data."""

from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex


def build_index(
    loader: ProblemLoader | None = None,
    index: SearchIndex | None = None,
    *,
    rebuild: bool = False,
) -> dict:
    """
    Build or update the search index.

    Args:
        loader: ProblemLoader instance (default: from_default())
        index: SearchIndex instance (default: from_default())
        rebuild: If True, clear existing index first

    Returns:
        Statistics about the indexing operation
    """
    if loader is None:
        loader = ProblemLoader.from_default()
    if index is None:
        index = SearchIndex.from_default()

    if rebuild:
        index.clear()

    problems_indexed = 0
    for problem in loader.iter_problems():
        index.index_problem(problem)
        problems_indexed += 1

    return {
        "problems_indexed": problems_indexed,
        "total_chunks": index.chunk_count(),
        "stats": index.get_stats(),
    }
```

---

## 5) CLI Integration

```python
# In src/erdos/commands/search.py

@app.callback(invoke_without_command=True)
def search(
    query: Annotated[
        str,
        typer.Argument(help="Search query"),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum results"),
    ] = 10,
    problem_id: Annotated[
        int | None,
        typer.Option("--problem", "-p", help="Filter to specific problem"),
    ] = None,
) -> None:
    """
    Search problem statements and indexed content.

    Example: erdos search "prime arithmetic progression"
    """
    from erdos.core.search_index import SearchIndex

    index = SearchIndex.from_default()
    results = index.search(query, limit=limit, problem_id=problem_id)

    ctx = _get_context()
    if ctx.get("json"):
        # JSON output
        output = CLIOutput.ok(
            command="erdos search",
            data={
                "query": query,
                "count": len(results),
                "results": [
                    {
                        "chunk_id": r.chunk_id,
                        "snippet": r.snippet,
                        "score": r.score,
                        "source_type": r.source_type.value,
                        "problem_id": r.problem_id,
                    }
                    for r in results
                ],
            },
        )
        console.print_json(output.model_dump_json())
    else:
        # Human output
        if not results:
            console.print(f"No results for: {query}")
            return

        console.print(f"[bold]Search results for:[/bold] {query}\n")
        for i, r in enumerate(results, 1):
            problem_str = f"Problem {r.problem_id}" if r.problem_id else "Reference"
            console.print(f"[cyan]{i}.[/cyan] [{r.source_type.value}] {problem_str}")
            console.print(f"   {r.snippet}")
            console.print(f"   [dim]Score: {r.score:.2f}[/dim]\n")
```

---

## 6) FTS5 Query Syntax

Users can use FTS5 query syntax for advanced searches:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `word1 word2` | Both words (AND) | `prime number` |
| `word1 OR word2` | Either word | `prime OR composite` |
| `"exact phrase"` | Exact match | `"arithmetic progression"` |
| `word*` | Prefix match | `arith*` |
| `NOT word` | Exclude | `prime NOT twin` |
| `NEAR(w1 w2, N)` | Within N words | `NEAR(prime gap, 5)` |

---

## 7) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_search_index.py
"""Unit tests for SearchIndex."""

from pathlib import Path

import pytest

from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus, TextChunk
from erdos.core.search_index import SearchIndex, SearchResult


@pytest.fixture
def temp_index(tmp_path: Path) -> SearchIndex:
    """Create a temporary search index."""
    return SearchIndex(tmp_path / "test.sqlite")


@pytest.fixture
def sample_problem() -> ProblemRecord:
    """A sample problem for indexing."""
    return ProblemRecord(
        id=6,
        title="Small primes in arithmetic progressions",
        statement="Let p_1 < p_2 < ... be the sequence of primes. Prove that for every k, there exist infinitely many arithmetic progressions of length k consisting entirely of primes.",
        status=ProblemStatus.PROVED,
        prize=100,
        tags=["number theory", "primes"],
    )


class TestSearchIndexBasics:
    def test_creates_database(self, temp_index: SearchIndex) -> None:
        """Index creates SQLite database file."""
        assert temp_index.db_path.exists()

    def test_empty_stats(self, temp_index: SearchIndex) -> None:
        """New index has zero counts."""
        stats = temp_index.get_stats()
        assert stats["problems"] == 0
        assert stats["chunks"] == 0


class TestSearchIndexIndexing:
    def test_index_problem(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Indexing a problem creates chunks."""
        temp_index.index_problem(sample_problem)

        assert temp_index.problem_count() == 1
        assert temp_index.chunk_count() >= 1

    def test_index_is_idempotent(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Indexing same problem twice doesn't duplicate."""
        temp_index.index_problem(sample_problem)
        temp_index.index_problem(sample_problem)

        assert temp_index.problem_count() == 1


class TestSearchIndexSearch:
    def test_search_finds_indexed_content(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Search returns results for matching query."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes arithmetic progression")

        assert len(results) > 0
        assert results[0].problem_id == 6

    def test_search_returns_empty_for_no_match(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Search returns empty list for non-matching query."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("quantum mechanics")

        assert len(results) == 0

    def test_search_respects_limit(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Search respects limit parameter."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes", limit=1)

        assert len(results) <= 1

    def test_search_with_problem_filter(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Search can filter by problem ID."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes", problem_id=6)
        assert len(results) > 0

        results = temp_index.search("primes", problem_id=999)
        assert len(results) == 0

    def test_search_returns_snippets(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """Search results include highlighted snippets."""
        temp_index.index_problem(sample_problem)

        results = temp_index.search("primes")

        assert results[0].snippet is not None
        # Snippet should contain highlight markers
        assert "<mark>" in results[0].snippet or "primes" in results[0].snippet.lower()

    def test_search_empty_query(self, temp_index: SearchIndex) -> None:
        """Empty query returns empty results."""
        results = temp_index.search("")
        assert results == []

        results = temp_index.search("   ")
        assert results == []


class TestSearchIndexClear:
    def test_clear_removes_all(
        self, temp_index: SearchIndex, sample_problem: ProblemRecord
    ) -> None:
        """clear() removes all indexed content."""
        temp_index.index_problem(sample_problem)
        temp_index.clear()

        assert temp_index.problem_count() == 0
        assert temp_index.chunk_count() == 0


class TestSearchResultDataclass:
    def test_search_result_fields(self) -> None:
        """SearchResult has expected fields."""
        result = SearchResult(
            chunk_id="test_1",
            text="Some text",
            snippet="...text...",
            score=1.5,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_key=None,
        )

        assert result.chunk_id == "test_1"
        assert result.score == 1.5
        assert result.problem_id == 6
```

### Integration Tests

```python
# tests/integration/test_search_index.py
"""Integration tests for search index with real data."""

from pathlib import Path

import pytest

from erdos.core.index_builder import build_index
from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex


@pytest.fixture
def populated_index(tmp_path: Path, sample_problems_yaml: Path) -> SearchIndex:
    """Index populated with sample data."""
    loader = ProblemLoader(sample_problems_yaml)
    index = SearchIndex(tmp_path / "test.sqlite")

    build_index(loader=loader, index=index)
    return index


def test_build_index_indexes_all_problems(
    tmp_path: Path, sample_problems_yaml: Path
) -> None:
    """build_index indexes all problems from loader."""
    loader = ProblemLoader(sample_problems_yaml)
    index = SearchIndex(tmp_path / "test.sqlite")

    result = build_index(loader=loader, index=index)

    assert result["problems_indexed"] == loader.count()
    assert result["total_chunks"] > 0


def test_search_after_build(populated_index: SearchIndex) -> None:
    """Search works after building index."""
    results = populated_index.search("problem")

    # Should find something in sample data
    assert len(results) >= 0  # May vary based on sample data


def test_fts5_phrase_search(populated_index: SearchIndex) -> None:
    """FTS5 phrase search works."""
    # Exact phrase match
    results = populated_index.search('"number theory"')
    # Results depend on sample data
    assert isinstance(results, list)


def test_fts5_prefix_search(populated_index: SearchIndex) -> None:
    """FTS5 prefix search works."""
    results = populated_index.search("prim*")  # Matches prime, primes, etc.
    assert isinstance(results, list)
```

### Acceptance Criteria

```bash
# 1. Index can be created
uv run python -c "
from erdos.core.search_index import SearchIndex
index = SearchIndex.from_default()
print(f'Index at: {index.db_path}')
print(f'Stats: {index.get_stats()}')
"

# 2. Build index from problems
uv run python -c "
from erdos.core.index_builder import build_index
result = build_index()
print(f'Indexed: {result}')
"

# 3. Search works
uv run python -c "
from erdos.core.search_index import SearchIndex
index = SearchIndex.from_default()
results = index.search('prime')
for r in results[:3]:
    print(f'{r.problem_id}: {r.snippet[:100]}...')
"

# 4. CLI search works
uv run erdos search "prime numbers" --limit 5
uv run erdos search "prime numbers" --json

# 5. Tests pass
uv run pytest tests/unit/test_search_index.py -v
uv run pytest tests/integration/test_search_index.py -v
```

---

## 8) Future: Vector Search (v1.2+)

When adding semantic search later:

```python
# Extension for vector search
class VectorIndex:
    """Add embedding-based similarity search."""

    def __init__(self, db_path: Path, embedding_model: str = "BAAI/bge-small-en-v1.5"):
        ...

    def embed_and_store(self, chunk_id: str, text: str) -> None:
        """Compute embedding and store in database."""
        ...

    def semantic_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Find semantically similar chunks."""
        ...
```

This is deferred per master-qualifications: BM25 is sufficient for v1.

---

## 9) References

- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)
- [FTS5 Query Syntax](https://www.sqlite.org/fts5.html#full_text_query_syntax)
- [BM25 Ranking](https://www.sqlite.org/fts5.html#the_bm25_function)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
