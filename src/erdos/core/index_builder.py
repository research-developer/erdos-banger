"""Build search index from problem data."""

from erdos.core.ports import ProblemRepository, SearchIndexProtocol


def build_index(
    *,
    loader: ProblemRepository,
    index: SearchIndexProtocol,
    rebuild: bool = False,
) -> dict[str, object]:
    """
    Build or update the search index.

    Args:
        loader: Problem repository
        index: Search index
        rebuild: If True, clear existing index first

    Returns:
        Statistics about the indexing operation
    """
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
