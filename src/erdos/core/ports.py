"""Core application ports (abstractions).

These Protocols define the interfaces that higher-level code (services/commands)
depends on, rather than concrete implementations like ProblemLoader/SearchIndex.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Iterator

    from erdos.core.models import ChunkSource, ProblemRecord
    from erdos.core.search_index import SearchResult


class ProblemRepository(Protocol):
    """Abstract interface for accessing Erdős problems."""

    def get_by_id(self, problem_id: int) -> ProblemRecord | None: ...

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]: ...

    def iter_problems(self) -> Iterator[ProblemRecord]: ...


class SearchIndexProtocol(Protocol):
    """Abstract interface for search operations."""

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]: ...

    def index_problem(self, problem: ProblemRecord) -> None: ...

    def problem_count(self) -> int: ...

    def chunk_count(self) -> int: ...

    def clear(self) -> None: ...

    def get_stats(self) -> dict[str, object]: ...
