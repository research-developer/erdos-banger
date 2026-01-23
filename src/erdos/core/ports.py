"""Core application ports (abstractions).

These Protocols define the interfaces that higher-level code (services/commands)
depends on, rather than concrete implementations like ProblemLoader/SearchIndex.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Iterator

    from erdos.core.models import ChunkSource, ProblemRecord, ReferenceRecord, TextChunk
    from erdos.core.search.types import (
        EmbeddingModelProtocol,
        SearchResult,
        SemanticSearchResult,
    )


class LLMExecute(Protocol):
    """Callable for executing an LLM command.

    This abstraction allows loop orchestration to depend on an interface
    rather than a concrete implementation (DIP compliance).
    """

    def __call__(
        self, llm_command: str, prompt: str, *, timeout: int | None = ...
    ) -> tuple[str, int]:
        """Execute an LLM command with the given prompt.

        Args:
            llm_command: Shell command to execute
            prompt: The prompt to pass via stdin
            timeout: Maximum seconds to wait (optional)

        Returns:
            Tuple of (answer, exit_code)
        """
        ...


class DOILookupProvider(Protocol):
    """Provider that can resolve metadata by DOI (ISP: single responsibility).

    Implementers: OpenAlexProvider, CrossrefProvider.
    Non-implementers: ArxivProvider (arXiv API doesn't support DOI lookup).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name for logging/debugging."""
        ...

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work metadata by DOI.

        Returns:
            ReferenceRecord if found, None if not found.

        Raises:
            requests.RequestException: On network/API errors (non-404).
            ValueError: On invalid identifiers or irrecoverable parse errors.
        """
        ...


class ArxivLookupProvider(Protocol):
    """Provider that can resolve metadata by arXiv ID (ISP: single responsibility).

    Implementers: OpenAlexProvider, ArxivProvider.
    Non-implementers: CrossrefProvider (Crossref doesn't index arXiv IDs).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name for logging/debugging."""
        ...

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch work metadata by arXiv ID.

        Note: This fetches METADATA about the arXiv paper (title, authors, etc.),
        not the source content. For content, use ArxivClient directly.

        Returns:
            ReferenceRecord if found, None if not found.

        Raises:
            requests.RequestException: On network/API errors (non-404).
            ValueError: On invalid arXiv identifiers or irrecoverable parse errors.
        """
        ...


class SearchableMetadataProvider(Protocol):
    """Provider that supports text search (ISP: single responsibility).

    Implementers: OpenAlexProvider.
    Non-implementers: ArxivProvider, CrossrefProvider (search not implemented).
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name for logging/debugging."""
        ...

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract.

        Returns:
            List of matching ReferenceRecords, possibly empty.
        """
        ...


class MetadataProvider(
    DOILookupProvider, ArxivLookupProvider, SearchableMetadataProvider, Protocol
):
    """Full provider supporting all three operations (backward-compatible aggregate).

    This protocol combines all metadata lookup capabilities for call sites that
    need the complete interface. Prefer using the focused protocols
    (DOILookupProvider, ArxivLookupProvider, SearchableMetadataProvider) when
    only a subset of operations is needed.

    Note: Protocol inheritance in Python typing creates a union of all methods.
    OpenAlexProvider and FallbackProvider both implement this full protocol.
    """

    ...


class ProblemRepository(Protocol):
    """Abstract interface for accessing Erdős problems."""

    def get_by_id(self, problem_id: int) -> ProblemRecord | None: ...

    def load_all(self, *, use_cache: bool = True) -> list[ProblemRecord]: ...

    def iter_problems(self) -> Iterator[ProblemRecord]: ...


class SearchIndexReadPort(Protocol):
    """Port for read-only search operations (ISP: search + stats).

    Use this port when you only need to query the index, not modify it.
    This is the minimal interface for retrieval operations (RAG, ask, etc.).
    """

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
        source_types: list[ChunkSource] | None = None,
    ) -> list[SearchResult]: ...

    def problem_count(self) -> int: ...

    def chunk_count(self) -> int: ...

    def get_stats(self) -> dict[str, object]: ...


class SearchIndexWritePort(Protocol):
    """Port for index mutation operations (ISP: indexing + clearing).

    Use this port when you need to build or modify the index.
    """

    def index_problem(self, problem: ProblemRecord) -> None: ...

    def index_chunk(self, chunk: TextChunk) -> None: ...

    def clear(self) -> None: ...


class EmbeddingIndexPort(Protocol):
    """Port for embedding-based search operations (ISP: semantic search).

    Use this port when you need embedding functionality (semantic/hybrid search).
    Note: build_embeddings() also requires SearchIndexReadPort for chunk iteration.
    """

    def has_embeddings(self) -> bool: ...

    def get_embedding_metadata(self) -> tuple[str | None, int | None]: ...

    def set_embedding_metadata(self, model_name: str, dimension: int) -> None: ...

    def build_embeddings(self, embedder: EmbeddingModelProtocol) -> int: ...

    def search_semantic(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]: ...

    def search_hybrid(
        self,
        query: str,
        embedder: EmbeddingModelProtocol,
        *,
        limit: int = 10,
        alpha: float = 0.5,
        problem_id: int | None = None,
    ) -> list[SemanticSearchResult]: ...


class SearchIndexProtocol(
    SearchIndexReadPort, SearchIndexWritePort, EmbeddingIndexPort, Protocol
):
    """Full search index interface (backward-compatible aggregate).

    This protocol combines all search capabilities for call sites that need
    the complete interface. Prefer using the focused ports (SearchIndexReadPort,
    SearchIndexWritePort, EmbeddingIndexPort) when possible.

    Note: Protocol inheritance in Python typing creates a union of all methods.
    SearchIndex implements this full protocol.
    """

    ...
