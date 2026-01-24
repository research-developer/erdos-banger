"""Embeddings wrapper for Lean Copilot /encode endpoint (SPEC-033).

This module provides embedding generation for premise retrieval in Lean Copilot.
It wraps the core embeddings module (SPEC-014) and provides clear degraded mode
when the 'embeddings' extra is not installed.

Requires the 'embeddings' optional dependency:
    uv sync --extra embeddings
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.search.embeddings import EmbeddingModel


logger = logging.getLogger(__name__)


# =============================================================================
# Availability Check
# =============================================================================


def is_embeddings_available() -> bool:
    """Check if embedding dependencies (sentence-transformers) are available."""
    try:
        from erdos.core.search.embeddings import EMBEDDING_AVAILABLE  # noqa: PLC0415

        return EMBEDDING_AVAILABLE
    except ImportError:
        logger.debug("Embeddings unavailable: sentence-transformers not installed")
        return False


# =============================================================================
# Exceptions
# =============================================================================


class EmbeddingsNotAvailableError(Exception):
    """Raised when embeddings functionality is requested but deps not installed."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "Embeddings functionality requires the 'embeddings' extra. "
                "Install with: uv sync --extra embeddings"
            )
        )


# =============================================================================
# Embedding Functions
# =============================================================================


_cached_model: EmbeddingModel | None = None
_model_lock = threading.Lock()


def get_embedding_model(model_name: str | None = None) -> EmbeddingModel:
    """Get the embedding model, using cache for efficiency.

    Args:
        model_name: Optional model name override. If None, uses the default
            (sentence-transformers/all-MiniLM-L6-v2).

    Returns:
        Configured EmbeddingModel instance.

    Raises:
        EmbeddingsNotAvailableError: If sentence-transformers not installed.
        ValueError: If model dimension mismatch.
    """
    global _cached_model  # noqa: PLW0603

    if not is_embeddings_available():
        raise EmbeddingsNotAvailableError()

    # Import here to avoid ImportError when embeddings extra not installed
    from erdos.core.search.embeddings import (  # noqa: PLC0415
        DEFAULT_MODEL_NAME,
        EmbeddingConfig,
        EmbeddingModel,
        EmbeddingNotAvailableError,
    )
    from erdos.core.search.embeddings_service import (  # noqa: PLC0415
        _get_model_dimension,
    )

    effective_model = model_name or DEFAULT_MODEL_NAME

    # Use cache if model name matches
    if _cached_model is not None and _cached_model.model_name == effective_model:
        return _cached_model

    with _model_lock:
        # Double-check after acquiring lock
        if _cached_model is not None and _cached_model.model_name == effective_model:
            return _cached_model

        try:
            dim = _get_model_dimension(effective_model)
            config = EmbeddingConfig(model_name=effective_model, dimension=dim)
            _cached_model = EmbeddingModel(config)
            return _cached_model
        except EmbeddingNotAvailableError as e:
            raise EmbeddingsNotAvailableError(str(e)) from e


def encode_texts(
    texts: list[str],
    *,
    model_name: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of texts to embed.
        model_name: Optional model name override.

    Returns:
        List of embedding vectors (each as list of floats).

    Raises:
        EmbeddingsNotAvailableError: If sentence-transformers not installed.
        ValueError: For invalid inputs or model errors.
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)
    embeddings = model.encode_batch(texts)

    # Convert numpy arrays to Python lists for JSON serialization
    return [emb.tolist() for emb in embeddings]


def clear_model_cache() -> None:
    """Clear the cached embedding model (useful for testing)."""
    global _cached_model  # noqa: PLW0603
    _cached_model = None


__all__ = [
    "EmbeddingsNotAvailableError",
    "clear_model_cache",
    "encode_texts",
    "get_embedding_model",
    "is_embeddings_available",
]
