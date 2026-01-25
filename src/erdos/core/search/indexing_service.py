"""Search index building service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError
from erdos.core.search.index_builder import build_index
from erdos.core.search.research_indexing import index_research_artifacts


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


logger = logging.getLogger(__name__)


def build_search_index(
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
    repo_root: Path | None = None,
    command: str = "erdos search",
) -> CLIOutput | None:
    """Build the search index.

    Args:
        repo: Problem repository
        index: Search index

    Returns:
        None on success, CLIOutput error on failure
    """
    try:
        build_index(loader=repo, index=index, rebuild=True)
        # Best-effort: index research artifacts into the same SQLite DB.
        # This must never prevent the base problem index from being usable.
        try:
            index_research_artifacts(repo=repo, index=index, repo_root=repo_root)
        except Exception:  # research indexing is best-effort
            logger.warning("Research indexing skipped due to error", exc_info=True)
        return None
    except (ProblemLoaderError, SearchIndexError) as e:
        error_type = (
            "LoaderError" if isinstance(e, ProblemLoaderError) else "IndexError"
        )
        return CLIOutput.err(
            command=command,
            error_type=error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )
