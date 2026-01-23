"""Search options and mode definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SearchMode(str, Enum):
    """Search mode selection."""

    BM25 = "bm25"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class SearchOptions:
    """Options for search operations."""

    query: str
    limit: int
    problem_id: int | None
    build_index: bool
    build_embeddings: bool = False
    mode: SearchMode = SearchMode.BM25
    alpha: float = 0.5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        """Validate options after initialization."""
        if self.limit <= 0:
            raise ValueError("limit must be greater than 0")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")
