"""Embedding model loading and embedding build services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.search.db import SearchIndexError
from erdos.core.search.facade import SearchIndex


if TYPE_CHECKING:
    from erdos.core.ports import SearchIndexProtocol
    from erdos.core.search.embeddings import EmbeddingModel


def get_embedding_model(
    model_name: str,
) -> tuple[EmbeddingModel | None, CLIOutput | None]:
    """Load embedding model, returning error if unavailable.

    Args:
        model_name: Name of the embedding model to load

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
        # Determine expected dimension based on model
        dim = 384 if "MiniLM" in model_name else 768
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
        index: Search index (must be SearchIndex instance)
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
        if isinstance(index, SearchIndex):
            count = index.build_embeddings(embedder)
            return count, None
        else:
            return 0, CLIOutput.err(
                command="erdos search",
                error_type="ConfigError",
                message="Embedding build requires SearchIndex instance",
                code=ExitCode.CONFIG_ERROR,
            )
    except SearchIndexError as e:
        return 0, CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message=str(e),
            code=ExitCode.ERROR,
        )
