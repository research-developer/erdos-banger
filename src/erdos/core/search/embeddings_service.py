"""Embedding model loading and embedding build services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.search.db import SearchIndexError


if TYPE_CHECKING:
    from erdos.core.ports import SearchIndexProtocol
    from erdos.core.search.embeddings import EmbeddingModel


# Model dimension registry for common embedding models
# Keys are substrings to match in model names, values are dimensions
_MODEL_DIMENSIONS: dict[str, int] = {
    "MiniLM": 384,
    "bge-small": 384,
    "bge-base": 768,
    "bge-large": 1024,
    "mpnet-base": 768,
    "e5-small": 384,
    "e5-base": 768,
    "e5-large": 1024,
}

# Default dimension for unknown models (most common size)
_DEFAULT_DIMENSION = 768


def _get_model_dimension(model_name: str) -> int:
    """Determine embedding dimension for a model.

    Args:
        model_name: The model name/path

    Returns:
        Expected embedding dimension
    """
    for pattern, dim in _MODEL_DIMENSIONS.items():
        if pattern in model_name:
            return dim
    return _DEFAULT_DIMENSION


def get_embedding_model(
    model_name: str,
    *,
    dimension: int | None = None,
) -> tuple[EmbeddingModel | None, CLIOutput | None]:
    """Load embedding model, returning error if unavailable.

    Args:
        model_name: Name of the embedding model to load
        dimension: Optional explicit dimension override

    Returns:
        Tuple of (model, error) - one will be None
    """
    # Local import to avoid import errors when embeddings deps not installed
    from erdos.core.search.embeddings import (  # noqa: PLC0415
        EMBEDDING_AVAILABLE,
        EmbeddingConfig,
        EmbeddingModel,
        EmbeddingNotAvailableError,
    )

    if not EMBEDDING_AVAILABLE:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=(
                "Embedding functionality requires the 'embeddings' extra. "
                "Install with: uv sync --extra embeddings"
            ),
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        # Use explicit dimension if provided, otherwise look up in registry
        dim = dimension if dimension is not None else _get_model_dimension(model_name)
        config = EmbeddingConfig(model_name=model_name, dimension=dim)
        model = EmbeddingModel(config)
        return model, None
    except EmbeddingNotAvailableError as e:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )
    except ValueError as e:
        return None, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message=str(e),
            code=ExitCode.CONFIG_ERROR,
        )


def build_embeddings(
    *,
    index: SearchIndexProtocol,
    model_name: str,
) -> tuple[int, CLIOutput | None]:
    """Build embeddings for indexed chunks.

    Args:
        index: Search index implementing SearchIndexProtocol
        model_name: Embedding model name

    Returns:
        Tuple of (count, error) - count is 0 if error occurred
    """
    embedder, err = get_embedding_model(model_name)
    if err:
        return 0, err
    if embedder is None:
        return 0, CLIOutput.err(
            command="erdos search",
            error_type="ConfigError",
            message="Failed to load embedding model",
            code=ExitCode.CONFIG_ERROR,
        )

    try:
        # Trust the protocol - if index has build_embeddings, use it
        count = index.build_embeddings(embedder)
        return count, None
    except SearchIndexError as e:
        return 0, CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )
