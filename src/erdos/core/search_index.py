"""SQLite FTS5 search index for erdos-banger."""

import json
import logging
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erdos.core.constants import PREVIEW_LENGTH
from erdos.core.models import ChunkSource, ProblemRecord, TextChunk


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    chunk_id: str
    text: str
    snippet: str  # Highlighted excerpt
    score: float  # BM25 score (higher = more relevant)
    source_type: ChunkSource
    problem_id: int | None
    reference_doi: str | None


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
        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Initializing search index at %s", db_path)
        self._ensure_schema()

    @classmethod
    def from_default(cls) -> "SearchIndex":
        """Create index using default path (index/erdos.sqlite)."""
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
            reference_doi TEXT,
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
            try:
                conn.executescript(schema_sql)
            except sqlite3.OperationalError as e:
                # Some Python builds link against SQLite without FTS5 enabled.
                # Fail fast with a clear message instead of a cryptic SQL error.
                if "fts5" in str(e).lower():
                    raise SearchIndexError(
                        "SQLite FTS5 is not available in this environment "
                        "(sqlite3 compiled without FTS5). "
                        "Use a Python/SQLite build with FTS5 enabled."
                    ) from e
                raise

    def index_problem(self, problem: ProblemRecord) -> None:
        """
        Index a problem's statement.

        Creates chunks for the problem statement and notes.

        Args:
            problem: The problem to index
        """
        now = datetime.now(UTC).isoformat()

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
                    preview=problem.notes[:PREVIEW_LENGTH]
                    if len(problem.notes) > PREVIEW_LENGTH
                    else problem.notes,
                )
                self._insert_chunk(conn, notes_chunk, now)

    def index_chunk(self, chunk: TextChunk) -> None:
        """
        Index a single text chunk.

        Args:
            chunk: The chunk to index
        """
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            self._insert_chunk(conn, chunk, now)

    def _insert_chunk(
        self, conn: sqlite3.Connection, chunk: TextChunk, timestamp: str
    ) -> None:
        """Insert a chunk into the database."""
        conn.execute(
            """
            INSERT OR REPLACE INTO chunks
            (id, text, source_type, problem_id, reference_doi, start_char, end_char, indexed_at)
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
                c.reference_doi
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c._rowid
            WHERE chunks_fts MATCH ?
        """
        params: list[str | int] = [query]

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
                        reference_doi=row["reference_doi"],
                    )
                )

        return results

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM problems")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def chunk_count(self) -> int:
        """Return number of indexed chunks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        """Delete all indexed content."""
        logger.info("Clearing search index")
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM problems")
            # Rebuild FTS index
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        logger.debug("Search index cleared")

    def rebuild_fts(self) -> None:
        """Rebuild the FTS index (use after direct SQL modifications)."""
        with self._connect() as conn:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

    def get_stats(self) -> dict[str, object]:
        """Get index statistics."""
        with self._connect() as conn:
            problems = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

            # Count by source type
            by_source: dict[str, int] = {}
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
                "db_size_bytes": self._db_path.stat().st_size
                if self._db_path.exists()
                else 0,
            }
