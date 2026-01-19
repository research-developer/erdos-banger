"""Unit tests for ask retrieval logic."""

from unittest.mock import MagicMock

from erdos.core.ask import perform_retrieval
from erdos.core.models import ChunkSource, ProblemRecord, ProblemStatus
from erdos.core.search_index import SearchIndex, SearchResult


def test_retrieval_calls_search_index():
    """perform_retrieval must call SearchIndex.search with correct params."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "What is known?"
    limit = 5

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = [
        SearchResult(
            chunk_id="test",
            text="result",
            snippet="...",
            score=1.0,
            source_type=ChunkSource.PROBLEM_STATEMENT,
            problem_id=6,
            reference_doi=None,
        )
    ]

    results = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=limit,
    )

    # Verify search was called with correct query and problem_id
    mock_index.search.assert_called_once()
    call_args = mock_index.search.call_args
    assert call_args.kwargs["limit"] == limit
    assert call_args.kwargs["problem_id"] == problem.id
    assert len(results) == 1
    assert results[0].chunk_id == "test"


def test_retrieval_constructs_query_from_problem_and_question():
    """Query should include problem title and question."""
    problem = ProblemRecord(
        id=6,
        title="Small primes",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "What partial results?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    # Verify query was constructed and search was called with problem_id filter
    call_args = mock_index.search.call_args
    query = call_args.args[0]
    # Query is the escaped question in quotes
    assert question in query
    # Problem ID should be passed as a filter
    assert call_args.kwargs["problem_id"] == problem.id


def test_retrieval_returns_empty_when_no_results():
    """perform_retrieval must handle empty search results."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    results = perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    assert results == []


def test_retrieval_respects_limit():
    """perform_retrieval must pass limit to search index."""
    problem = ProblemRecord(
        id=6,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=10,
    )

    call_args = mock_index.search.call_args
    assert call_args.kwargs["limit"] == 10


def test_retrieval_filters_by_problem_id():
    """perform_retrieval must filter to the specified problem."""
    problem = ProblemRecord(
        id=42,
        title="Test",
        statement="Test statement",
        status=ProblemStatus.OPEN,
    )
    question = "Test?"

    mock_index = MagicMock(spec=SearchIndex)
    mock_index.search.return_value = []

    perform_retrieval(
        index=mock_index,
        problem=problem,
        question=question,
        limit=5,
    )

    call_args = mock_index.search.call_args
    assert call_args.kwargs["problem_id"] == 42
