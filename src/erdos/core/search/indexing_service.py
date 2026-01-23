"""Search index building service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search.db import SearchIndexError
from erdos.core.search.index_builder import build_index


if TYPE_CHECKING:
    from erdos.core.ports import ProblemRepository, SearchIndexProtocol


def build_search_index(
    *,
    repo: ProblemRepository,
    index: SearchIndexProtocol,
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
        return None
    except (ProblemLoaderError, SearchIndexError) as e:
        error_type = (
            "LoaderError" if isinstance(e, ProblemLoaderError) else "IndexError"
        )
        return CLIOutput.err(
            command="erdos search",
            error_type=error_type,
            message=str(e),
            code=ExitCode.ERROR,
        )
