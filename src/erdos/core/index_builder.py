"""Build search index from problem data."""

from erdos.core.problem_loader import ProblemLoader
from erdos.core.search_index import SearchIndex


def build_index(
    loader: ProblemLoader | None = None,
    index: SearchIndex | None = None,
    *,
    rebuild: bool = False,
) -> dict[str, object]:
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
