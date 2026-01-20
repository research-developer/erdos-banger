"""Unit tests for erdos search command helpers (DEBT-017-D4)."""

from __future__ import annotations

from unittest import mock

from erdos.commands.search import (
    SearchOptions,
    _build_index_if_requested,
    _search_with_fallback,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import CLIOutput
from erdos.core.problem_loader import ProblemLoaderError
from erdos.core.search_index import SearchIndexError


class TestSearchOptions:
    """Tests for SearchOptions dataclass."""

    def test_all_fields(self) -> None:
        """Should create options with all fields."""
        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=6,
            build_index=True,
        )
        assert options.query == "prime"
        assert options.limit == 10
        assert options.problem_id == 6
        assert options.build_index is True

    def test_none_problem_id(self) -> None:
        """Should handle None problem_id."""
        options = SearchOptions(
            query="test",
            limit=5,
            problem_id=None,
            build_index=False,
        )
        assert options.problem_id is None


class TestBuildIndexIfRequested:
    """Tests for _build_index_if_requested() helper."""

    def test_no_build_returns_none(self) -> None:
        """Should return None when build_index is False."""
        console = mock.Mock()
        result = _build_index_if_requested(False, console)
        assert result is None
        console.print.assert_not_called()

    @mock.patch("erdos.commands.search.do_build_index")
    def test_successful_build(self, mock_build: mock.Mock) -> None:
        """Should return None and print progress on successful build."""
        mock_build.return_value = {"problems_indexed": 100}
        console = mock.Mock()

        result = _build_index_if_requested(True, console)

        assert result is None
        mock_build.assert_called_once_with(rebuild=True)
        assert console.print.call_count == 2
        assert "Building search index" in str(console.print.call_args_list[0])

    @mock.patch("erdos.commands.search.do_build_index")
    def test_loader_error(self, mock_build: mock.Mock) -> None:
        """Should return CLIOutput error on ProblemLoaderError."""
        mock_build.side_effect = ProblemLoaderError("Problems not found")
        console = mock.Mock()

        result = _build_index_if_requested(True, console)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "LoaderError"
        assert "Problems not found" in result.error["message"]
        assert result.error["code"] == ExitCode.ERROR

    @mock.patch("erdos.commands.search.do_build_index")
    def test_index_error(self, mock_build: mock.Mock) -> None:
        """Should return CLIOutput error on SearchIndexError."""
        mock_build.side_effect = SearchIndexError("Index corrupted")
        console = mock.Mock()

        result = _build_index_if_requested(True, console)

        assert result is not None
        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "IndexError"
        assert "Index corrupted" in result.error["message"]
        assert result.error["code"] == ExitCode.ERROR


class TestSearchWithFallback:
    """Tests for _search_with_fallback() helper."""

    @mock.patch("erdos.commands.search.search_problems_fts")
    def test_successful_fts_search(self, mock_fts: mock.Mock) -> None:
        """Should return FTS result when successful."""
        expected_result = CLIOutput.ok(
            "erdos search",
            {"query": "prime", "count": 1, "results": [], "use_fts": True},
        )
        mock_fts.return_value = expected_result

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = _search_with_fallback(options)

        assert result.success is True
        mock_fts.assert_called_once_with("prime", limit=10, problem_id=None)

    @mock.patch("erdos.commands.search.search_problems_basic")
    @mock.patch("erdos.commands.search.ProblemLoader")
    @mock.patch("erdos.commands.search.search_problems_fts")
    def test_fallback_to_basic_on_empty_index(
        self, mock_fts: mock.Mock, mock_loader_cls: mock.Mock, mock_basic: mock.Mock
    ) -> None:
        """Should fall back to basic search when index is empty."""
        mock_fts.return_value = CLIOutput.err(
            command="erdos search",
            error_type="IndexEmpty",
            message="Index is empty",
            code=0,
        )
        mock_loader = mock.Mock()
        mock_loader_cls.from_default.return_value = mock_loader
        expected_result = CLIOutput.ok(
            "erdos search",
            {"query": "prime", "count": 0, "results": [], "use_fts": False},
        )
        mock_basic.return_value = expected_result

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = _search_with_fallback(options)

        assert result.success is True
        mock_basic.assert_called_once_with("prime", mock_loader, 10)

    @mock.patch("erdos.commands.search.ProblemLoader")
    @mock.patch("erdos.commands.search.search_problems_fts")
    def test_fallback_loader_error(
        self, mock_fts: mock.Mock, mock_loader_cls: mock.Mock
    ) -> None:
        """Should return error when fallback loader fails."""
        mock_fts.return_value = CLIOutput.err(
            command="erdos search",
            error_type="IndexEmpty",
            message="Index is empty",
            code=0,
        )
        mock_loader_cls.from_default.side_effect = ProblemLoaderError("Not found")

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = _search_with_fallback(options)

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "LoaderError"

    @mock.patch("erdos.commands.search.search_problems_fts")
    def test_non_empty_index_error_not_fallback(self, mock_fts: mock.Mock) -> None:
        """Should not fall back for non-IndexEmpty errors."""
        mock_fts.return_value = CLIOutput.err(
            command="erdos search",
            error_type="IndexError",
            message="Some other error",
            code=ExitCode.ERROR,
        )

        options = SearchOptions(
            query="prime",
            limit=10,
            problem_id=None,
            build_index=False,
        )
        result = _search_with_fallback(options)

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "IndexError"

    @mock.patch("erdos.commands.search.search_problems_fts")
    def test_passes_problem_id_filter(self, mock_fts: mock.Mock) -> None:
        """Should pass problem_id filter to FTS search."""
        mock_fts.return_value = CLIOutput.ok(
            "erdos search",
            {"query": "test", "count": 0, "results": [], "use_fts": True},
        )

        options = SearchOptions(
            query="test",
            limit=5,
            problem_id=42,
            build_index=False,
        )
        _search_with_fallback(options)

        mock_fts.assert_called_once_with("test", limit=5, problem_id=42)
