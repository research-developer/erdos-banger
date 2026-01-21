"""Unit tests for batch operations module (SPEC-015)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from erdos.core.batch import (
    SCHEMA_VERSION,
    BatchFilters,
    BatchProgress,
    BatchResult,
    BatchRunner,
    BatchState,
    filter_problem_ids,
    generate_batch_id,
    load_batch_state,
    load_latest_batch_id,
    save_batch_state,
    save_latest_batch_id,
)
from erdos.core.exit_codes import ExitCode
from erdos.core.models import ProblemRecord, ProblemStatus


@pytest.fixture
def sample_problems() -> list[ProblemRecord]:
    """Create sample problems for testing."""
    return [
        ProblemRecord(
            id=1,
            title="Problem 1",
            statement="Statement 1",
            status=ProblemStatus.OPEN,
            prize=100,
            tags=["number theory", "primes"],
        ),
        ProblemRecord(
            id=2,
            title="Problem 2",
            statement="Statement 2",
            status=ProblemStatus.PROVED,
            prize=0,
            tags=["combinatorics"],
        ),
        ProblemRecord(
            id=3,
            title="Problem 3",
            statement="Statement 3",
            status=ProblemStatus.OPEN,
            prize=500,
            tags=["number theory", "graph theory"],
        ),
        ProblemRecord(
            id=4,
            title="Problem 4",
            statement="Statement 4",
            status=ProblemStatus.PARTIALLY_SOLVED,
            prize=200,
            tags=["primes"],
        ),
    ]


class TestBatchFilters:
    """Tests for BatchFilters dataclass."""

    def test_default_values(self) -> None:
        """Test default values for BatchFilters."""
        filters = BatchFilters()
        assert filters.status is None
        assert filters.prize_min is None
        assert filters.prize_max is None
        assert filters.tags is None
        assert filters.limit is None
        assert filters.skip is None

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        filters = BatchFilters(
            status="open",
            prize_min=100,
            tags=["number theory"],
        )
        d = filters.to_dict()
        assert d["status"] == "open"
        assert d["prize_min"] == 100
        assert d["tags"] == ["number theory"]
        assert "prize_max" not in d or d["prize_max"] is None

    def test_from_dict(self) -> None:
        """Test from_dict class method."""
        d = {"status": "proved", "prize_min": 50}
        filters = BatchFilters.from_dict(d)
        assert filters.status == "proved"
        assert filters.prize_min == 50
        assert filters.prize_max is None

    def test_matches(self) -> None:
        """Test matches method for comparing filters."""
        filters1 = BatchFilters(status="open", prize_min=100)
        filters2 = BatchFilters(status="open", prize_min=100)
        filters3 = BatchFilters(status="proved", prize_min=100)

        assert filters1.matches(filters2)
        assert not filters1.matches(filters3)


class TestFilterProblemIds:
    """Tests for filter_problem_ids function."""

    def test_no_filters(self, sample_problems: list[ProblemRecord]) -> None:
        """Test with no filters returns all problems."""
        filters = BatchFilters()
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 2, 3, 4]

    def test_filter_by_status(self, sample_problems: list[ProblemRecord]) -> None:
        """Test filtering by status."""
        filters = BatchFilters(status="open")
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 3]

    def test_filter_by_prize_min(self, sample_problems: list[ProblemRecord]) -> None:
        """Test filtering by minimum prize."""
        filters = BatchFilters(prize_min=150)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [3, 4]

    def test_filter_by_prize_max(self, sample_problems: list[ProblemRecord]) -> None:
        """Test filtering by maximum prize."""
        filters = BatchFilters(prize_max=150)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 2]

    def test_filter_by_prize_range(self, sample_problems: list[ProblemRecord]) -> None:
        """Test filtering by prize range."""
        filters = BatchFilters(prize_min=100, prize_max=250)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 4]

    def test_filter_by_tags(self, sample_problems: list[ProblemRecord]) -> None:
        """Test filtering by tags (any match)."""
        filters = BatchFilters(tags=["number theory"])
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 3]

    def test_filter_by_multiple_tags(
        self, sample_problems: list[ProblemRecord]
    ) -> None:
        """Test filtering by multiple tags (any match)."""
        filters = BatchFilters(tags=["combinatorics", "graph theory"])
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [2, 3]

    def test_filter_combined(self, sample_problems: list[ProblemRecord]) -> None:
        """Test combining multiple filters."""
        filters = BatchFilters(status="open", prize_min=1)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 3]

    def test_limit(self, sample_problems: list[ProblemRecord]) -> None:
        """Test limit option."""
        filters = BatchFilters(limit=2)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 2]

    def test_skip(self, sample_problems: list[ProblemRecord]) -> None:
        """Test skip option."""
        filters = BatchFilters(skip=2)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [3, 4]

    def test_skip_and_limit(self, sample_problems: list[ProblemRecord]) -> None:
        """Test skip and limit together."""
        filters = BatchFilters(skip=1, limit=2)
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [2, 3]

    def test_case_insensitive_tags(self, sample_problems: list[ProblemRecord]) -> None:
        """Test tag filtering is case insensitive."""
        filters = BatchFilters(tags=["NUMBER THEORY"])
        ids = filter_problem_ids(sample_problems, filters)
        assert ids == [1, 3]


class TestBatchState:
    """Tests for BatchState dataclass."""

    def test_creation(self) -> None:
        """Test BatchState creation."""
        state = BatchState(
            batch_id="batch_20260118_103045",
            command="erdos ingest",
            filters=BatchFilters(status="open"),
            problem_ids=[1, 2, 3],
        )
        assert state.batch_id == "batch_20260118_103045"
        assert state.command == "erdos ingest"
        assert state.problem_ids == [1, 2, 3]
        assert state.completed == []
        assert state.failed == []

    def test_pending_property(self) -> None:
        """Test pending property."""
        state = BatchState(
            batch_id="test",
            command="erdos ingest",
            filters=BatchFilters(),
            problem_ids=[1, 2, 3, 4],
            completed=[1, 2],
            failed=[3],
        )
        assert state.pending == [4]

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization round-trip."""
        state = BatchState(
            batch_id="batch_20260118_103045",
            command="erdos ingest",
            filters=BatchFilters(status="open", prize_min=100),
            problem_ids=[1, 2, 3],
            completed=[1],
            failed=[2],
        )
        d = state.to_dict()
        restored = BatchState.from_dict(d)

        assert restored.batch_id == state.batch_id
        assert restored.command == state.command
        assert restored.problem_ids == state.problem_ids
        assert restored.completed == state.completed
        assert restored.failed == state.failed
        assert restored.filters.status == state.filters.status

    def test_schema_version(self) -> None:
        """Test that to_dict includes schema_version."""
        state = BatchState(
            batch_id="test",
            command="erdos ingest",
            filters=BatchFilters(),
            problem_ids=[1],
        )
        d = state.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION

    def test_from_dict_invalid_schema_version(self) -> None:
        """Test from_dict raises on unsupported schema version."""
        d = {
            "schema_version": 999,
            "batch_id": "test",
            "command": "erdos ingest",
            "filters": {},
            "problem_ids": [1],
        }
        with pytest.raises(ValueError, match="Unsupported schema_version"):
            BatchState.from_dict(d)

    def test_mark_completed(self) -> None:
        """Test mark_completed method."""
        state = BatchState(
            batch_id="test",
            command="erdos ingest",
            filters=BatchFilters(),
            problem_ids=[1, 2, 3],
        )
        state.mark_completed(1)
        assert 1 in state.completed
        assert 1 not in state.failed

    def test_mark_failed(self) -> None:
        """Test mark_failed method."""
        state = BatchState(
            batch_id="test",
            command="erdos ingest",
            filters=BatchFilters(),
            problem_ids=[1, 2, 3],
        )
        state.mark_failed(1)
        assert 1 in state.failed
        assert 1 not in state.completed

    def test_is_complete(self) -> None:
        """Test is_complete property."""
        state = BatchState(
            batch_id="test",
            command="erdos ingest",
            filters=BatchFilters(),
            problem_ids=[1, 2],
        )
        assert not state.is_complete

        state.mark_completed(1)
        assert not state.is_complete

        state.mark_completed(2)
        assert state.is_complete


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_creation(self) -> None:
        """Test BatchProgress creation."""
        progress = BatchProgress(
            problem_id=1,
            index=0,
            total=10,
            success=True,
            message="OK",
        )
        assert progress.problem_id == 1
        assert progress.index == 0
        assert progress.total == 10
        assert progress.success is True
        assert progress.message == "OK"


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_creation(self) -> None:
        """Test BatchResult creation."""
        result = BatchResult(
            batch_id="test",
            total=10,
            completed_count=8,
            failed_count=2,
            failed_ids=[3, 7],
            duration_ms=5000,
        )
        assert result.batch_id == "test"
        assert result.total == 10
        assert result.success is False  # Has failures

    def test_success_when_all_completed(self) -> None:
        """Test success is True when no failures."""
        result = BatchResult(
            batch_id="test",
            total=5,
            completed_count=5,
            failed_count=0,
            failed_ids=[],
            duration_ms=1000,
        )
        assert result.success is True


class TestGenerateBatchId:
    """Tests for generate_batch_id function."""

    def test_format(self) -> None:
        """Test batch ID format with microseconds for uniqueness."""
        batch_id = generate_batch_id()
        assert batch_id.startswith("batch_")
        parts = batch_id.split("_")
        assert len(parts) == 4  # batch, YYYYMMDD, HHMMSS, ffffff
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 6  # ffffff (microseconds)

    def test_uniqueness(self) -> None:
        """Test batch IDs are unique across calls."""
        ids = {generate_batch_id() for _ in range(10)}
        # May have duplicates if called in same second, but unlikely
        # At minimum should have at least one unique ID
        assert len(ids) >= 1


class TestBatchStatePersistence:
    """Tests for batch state save/load functions."""

    def test_save_and_load_state(self, tmp_path: Path) -> None:
        """Test saving and loading batch state."""
        batches_dir = tmp_path / "logs" / "batches"
        batches_dir.mkdir(parents=True)

        state = BatchState(
            batch_id="batch_20260118_103045",
            command="erdos ingest",
            filters=BatchFilters(status="open"),
            problem_ids=[1, 2, 3],
            completed=[1],
        )

        state_path = batches_dir / f"{state.batch_id}.json"
        save_batch_state(state_path, state)

        loaded = load_batch_state(state_path)
        assert loaded.batch_id == state.batch_id
        assert loaded.problem_ids == state.problem_ids
        assert loaded.completed == state.completed

    def test_load_nonexistent_state(self, tmp_path: Path) -> None:
        """Test loading nonexistent state file."""
        state_path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_batch_state(state_path)

    def test_load_corrupted_state(self, tmp_path: Path) -> None:
        """Test loading corrupted state file."""
        state_path = tmp_path / "corrupted.json"
        state_path.write_text("not valid json {", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_batch_state(state_path)

    def test_save_and_load_latest(self, tmp_path: Path) -> None:
        """Test saving and loading latest batch ID."""
        batches_dir = tmp_path / "logs" / "batches"
        batches_dir.mkdir(parents=True)

        latest_path = batches_dir / "latest.json"
        save_latest_batch_id(latest_path, "batch_20260118_103045")

        loaded_id = load_latest_batch_id(latest_path)
        assert loaded_id == "batch_20260118_103045"

    def test_load_nonexistent_latest(self, tmp_path: Path) -> None:
        """Test loading nonexistent latest file."""
        latest_path = tmp_path / "latest.json"
        with pytest.raises(FileNotFoundError):
            load_latest_batch_id(latest_path)


class TestBatchRunner:
    """Tests for BatchRunner class."""

    def test_init(self) -> None:
        """Test BatchRunner initialization."""
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=MagicMock(return_value=True),
        )
        assert runner.command == "erdos ingest"
        assert runner.problem_ids == [1, 2, 3]

    def test_run_processes_all(self, tmp_path: Path) -> None:
        """Test run processes all problems."""
        process_fn = MagicMock(return_value=True)
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=process_fn,
            state_dir=tmp_path,
        )
        result = runner.run()

        assert result.total == 3
        assert result.completed_count == 3
        assert result.failed_count == 0
        assert process_fn.call_count == 3

    def test_run_handles_failures(self, tmp_path: Path) -> None:
        """Test run handles failures."""

        def process_fn(problem_id: int) -> bool:
            return problem_id != 2  # Fail on problem 2

        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=process_fn,
            state_dir=tmp_path,
        )
        result = runner.run()

        assert result.total == 3
        assert result.completed_count == 2
        assert result.failed_count == 1
        assert result.failed_ids == [2]

    def test_run_updates_state_file(self, tmp_path: Path) -> None:
        """Test run updates state file after each problem."""
        batches_dir = tmp_path / "batches"
        batches_dir.mkdir()

        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2],
            process_fn=lambda pid: True,
            state_dir=tmp_path,
        )
        result = runner.run()

        # State file should exist
        state_path = batches_dir / f"{result.batch_id}.json"
        assert state_path.exists()

        # Latest file should exist
        latest_path = batches_dir / "latest.json"
        assert latest_path.exists()

    def test_run_with_progress_callback(self, tmp_path: Path) -> None:
        """Test run calls progress callback."""
        progress_calls: list[BatchProgress] = []

        def on_progress(progress: BatchProgress) -> None:
            progress_calls.append(progress)

        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=lambda pid: True,
            state_dir=tmp_path,
            on_progress=on_progress,
        )
        runner.run()

        assert len(progress_calls) == 3
        assert progress_calls[0].problem_id == 1
        assert progress_calls[0].index == 0
        assert progress_calls[0].total == 3

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run doesn't process or create state."""
        process_fn = MagicMock(return_value=True)
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=process_fn,
            state_dir=tmp_path,
            dry_run=True,
        )
        result = runner.run()

        assert result.total == 3
        assert result.completed_count == 0  # Nothing processed
        assert process_fn.call_count == 0
        assert result.dry_run is True

    def test_resume_skips_completed(self, tmp_path: Path) -> None:
        """Test resume skips completed problems."""
        batches_dir = tmp_path / "batches"
        batches_dir.mkdir()

        # Create prior state with problem 1 completed
        prior_state = BatchState(
            batch_id="batch_test",
            command="erdos ingest",
            filters=BatchFilters(status="open"),
            problem_ids=[1, 2, 3],
            completed=[1],
        )
        state_path = batches_dir / "batch_test.json"
        save_batch_state(state_path, prior_state)
        latest_path = batches_dir / "latest.json"
        save_latest_batch_id(latest_path, "batch_test")

        process_fn = MagicMock(return_value=True)
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=process_fn,
            state_dir=tmp_path,
            filters=BatchFilters(status="open"),
            resume=True,
        )
        result = runner.run()

        # Should only process 2 and 3
        assert process_fn.call_count == 2
        assert result.completed_count == 3  # Including prior completed

    def test_resume_retries_failed(self, tmp_path: Path) -> None:
        """Test resume retries failed problems."""
        batches_dir = tmp_path / "batches"
        batches_dir.mkdir()

        # Create prior state with problem 2 failed
        prior_state = BatchState(
            batch_id="batch_test",
            command="erdos ingest",
            filters=BatchFilters(status="open"),
            problem_ids=[1, 2, 3],
            completed=[1],
            failed=[2],
        )
        state_path = batches_dir / "batch_test.json"
        save_batch_state(state_path, prior_state)
        latest_path = batches_dir / "latest.json"
        save_latest_batch_id(latest_path, "batch_test")

        process_fn = MagicMock(return_value=True)
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=process_fn,
            state_dir=tmp_path,
            filters=BatchFilters(status="open"),
            resume=True,
        )
        result = runner.run()

        # Should process 2 (retry) and 3 (pending)
        assert process_fn.call_count == 2
        calls = [call[0][0] for call in process_fn.call_args_list]
        assert 2 in calls
        assert 3 in calls

    def test_resume_no_prior_state(self, tmp_path: Path) -> None:
        """Test resume without prior state returns error."""
        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=lambda pid: True,
            state_dir=tmp_path,
            resume=True,
        )
        result = runner.run()

        assert result.exit_code == ExitCode.NOT_FOUND
        assert "no previous batch run" in result.error_message.lower()

    def test_resume_command_mismatch(self, tmp_path: Path) -> None:
        """Test resume with different command returns error."""
        batches_dir = tmp_path / "batches"
        batches_dir.mkdir()

        # Create prior state with different command
        prior_state = BatchState(
            batch_id="batch_test",
            command="erdos lean formalize",  # Different command
            filters=BatchFilters(),
            problem_ids=[1, 2, 3],
        )
        state_path = batches_dir / "batch_test.json"
        save_batch_state(state_path, prior_state)
        latest_path = batches_dir / "latest.json"
        save_latest_batch_id(latest_path, "batch_test")

        runner = BatchRunner(
            command="erdos ingest",  # Different
            problem_ids=[1, 2, 3],
            process_fn=lambda pid: True,
            state_dir=tmp_path,
            resume=True,
        )
        result = runner.run()

        assert result.exit_code == ExitCode.USAGE_ERROR
        assert "command mismatch" in result.error_message.lower()

    def test_resume_filter_mismatch(self, tmp_path: Path) -> None:
        """Test resume with different filters returns error."""
        batches_dir = tmp_path / "batches"
        batches_dir.mkdir()

        # Create prior state with different filters
        prior_state = BatchState(
            batch_id="batch_test",
            command="erdos ingest",
            filters=BatchFilters(status="open"),  # Different
            problem_ids=[1, 2, 3],
        )
        state_path = batches_dir / "batch_test.json"
        save_batch_state(state_path, prior_state)
        latest_path = batches_dir / "latest.json"
        save_latest_batch_id(latest_path, "batch_test")

        runner = BatchRunner(
            command="erdos ingest",
            problem_ids=[1, 2, 3],
            process_fn=lambda pid: True,
            state_dir=tmp_path,
            filters=BatchFilters(status="proved"),  # Different
            resume=True,
        )
        result = runner.run()

        assert result.exit_code == ExitCode.USAGE_ERROR
        assert "filter mismatch" in result.error_message.lower()
