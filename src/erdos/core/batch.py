"""Batch operations for ingest and formalize commands (SPEC-015).

Provides batch processing with filtering, state tracking, and resume support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erdos.core.exit_codes import ExitCode
from erdos.core.models import ProblemStatus
from erdos.core.rate_limiter import RateLimiter


if TYPE_CHECKING:
    from collections.abc import Callable

    from erdos.core.models import ProblemRecord

logger = logging.getLogger(__name__)

# Schema version for batch state files
SCHEMA_VERSION = 1


@dataclass
class BatchFilters:
    """Filters for selecting problems in batch operations."""

    status: str | None = None
    prize_min: int | None = None
    prize_max: int | None = None
    tags: list[str] | None = None
    limit: int | None = None
    skip: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "prize_min": self.prize_min,
            "prize_max": self.prize_max,
            "tags": self.tags,
            "limit": self.limit,
            "skip": self.skip,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchFilters:
        """Create from dictionary."""
        return cls(
            status=d.get("status"),
            prize_min=d.get("prize_min"),
            prize_max=d.get("prize_max"),
            tags=d.get("tags"),
            limit=d.get("limit"),
            skip=d.get("skip"),
        )

    def matches(self, other: BatchFilters) -> bool:
        """Check if filters match (for resume validation)."""
        # Use set comparison for tags to ignore ordering differences
        self_tags = set(self.tags) if self.tags else set()
        other_tags = set(other.tags) if other.tags else set()
        return (
            self.status == other.status
            and self.prize_min == other.prize_min
            and self.prize_max == other.prize_max
            and self_tags == other_tags
            # limit/skip not compared since they may differ on resume
        )


def filter_problem_ids(
    problems: list[ProblemRecord], filters: BatchFilters
) -> list[int]:
    """Filter problems by criteria and return matching IDs.

    Args:
        problems: List of ProblemRecord objects
        filters: Filter criteria to apply

    Returns:
        List of matching problem IDs
    """
    results: list[int] = []

    for problem in problems:
        # Filter by status
        if filters.status is not None:
            expected_status = ProblemStatus.from_string(filters.status)
            if problem.status != expected_status:
                continue

        # Filter by prize range
        if filters.prize_min is not None and problem.prize < filters.prize_min:
            continue
        if filters.prize_max is not None and problem.prize > filters.prize_max:
            continue

        # Filter by tags (any match, case insensitive)
        if filters.tags:
            tag_set = {t.lower() for t in filters.tags}
            problem_tags = {t.lower() for t in problem.tags}
            if not tag_set.intersection(problem_tags):
                continue

        results.append(problem.id)

    # Apply skip/limit after filtering
    if filters.skip:
        results = results[filters.skip :]
    if filters.limit:
        results = results[: filters.limit]

    return results


@dataclass
class BatchState:
    """State of a batch operation for persistence and resume."""

    batch_id: str
    command: str
    filters: BatchFilters
    problem_ids: list[int]
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed: list[int] = field(default_factory=list)
    failed: list[int] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def pending(self) -> list[int]:
        """Return IDs that haven't been processed yet."""
        processed = set(self.completed) | set(self.failed)
        return [pid for pid in self.problem_ids if pid not in processed]

    @property
    def is_complete(self) -> bool:
        """Return True if all problems have been processed."""
        return len(self.pending) == 0

    def mark_completed(self, problem_id: int) -> None:
        """Mark a problem as successfully completed."""
        if problem_id not in self.completed:
            self.completed.append(problem_id)
        # Remove from failed if present (on retry success)
        if problem_id in self.failed:
            self.failed.remove(problem_id)
        self.last_updated = datetime.now(tz=UTC)

    def mark_failed(self, problem_id: int) -> None:
        """Mark a problem as failed."""
        if problem_id not in self.failed:
            self.failed.append(problem_id)
        self.last_updated = datetime.now(tz=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": SCHEMA_VERSION,
            "batch_id": self.batch_id,
            "command": self.command,
            "filters": self.filters.to_dict(),
            "started_at": self.started_at.isoformat(),
            "problem_ids": self.problem_ids,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchState:
        """Create from dictionary.

        Raises:
            ValueError: If schema_version is unsupported
        """
        schema_version = d.get("schema_version", 1)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version {schema_version}, expected {SCHEMA_VERSION}"
            )

        started_at = d.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = datetime.now(tz=UTC)

        last_updated = d.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        else:
            last_updated = datetime.now(tz=UTC)

        return cls(
            batch_id=d["batch_id"],
            command=d["command"],
            filters=BatchFilters.from_dict(d.get("filters", {})),
            problem_ids=d["problem_ids"],
            started_at=started_at,
            completed=d.get("completed", []),
            failed=d.get("failed", []),
            last_updated=last_updated,
        )


@dataclass
class BatchProgress:
    """Progress update for batch operations."""

    problem_id: int
    index: int
    total: int
    success: bool
    message: str


@dataclass
class BatchResult:
    """Result of a batch operation."""

    batch_id: str
    total: int
    completed_count: int
    failed_count: int
    failed_ids: list[int]
    duration_ms: int
    dry_run: bool = False
    exit_code: ExitCode = ExitCode.SUCCESS
    error_message: str = ""

    @property
    def success(self) -> bool:
        """Return True if all problems succeeded (no failures)."""
        return self.failed_count == 0 and self.exit_code == ExitCode.SUCCESS


def generate_batch_id() -> str:
    """Generate a unique batch ID based on current timestamp.

    Returns:
        Batch ID in format: batch_YYYYMMDD_HHMMSS_ffffff (includes microseconds)
    """
    now = datetime.now(tz=UTC)
    return f"batch_{now.strftime('%Y%m%d_%H%M%S_%f')}"


def save_batch_state(path: Path, state: BatchState) -> None:
    """Save batch state to JSON file.

    Args:
        path: Path to save state file
        state: BatchState to save
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    logger.debug("Saved batch state to %s", path)


def load_batch_state(path: Path) -> BatchState:
    """Load batch state from JSON file.

    Args:
        path: Path to state file

    Returns:
        BatchState loaded from file

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        ValueError: If schema_version is unsupported
    """
    content = path.read_text(encoding="utf-8")
    d = json.loads(content)
    return BatchState.from_dict(d)


def save_latest_batch_id(path: Path, batch_id: str) -> None:
    """Save latest batch ID to pointer file.

    Args:
        path: Path to latest.json file
        batch_id: Batch ID to save
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"batch_id": batch_id}), encoding="utf-8")


def load_latest_batch_id(path: Path) -> str:
    """Load latest batch ID from pointer file.

    Args:
        path: Path to latest.json file

    Returns:
        Batch ID string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    content = path.read_text(encoding="utf-8")
    d: dict[str, Any] = json.loads(content)
    batch_id: str = d["batch_id"]
    return batch_id


class BatchRunner:
    """Runs batch operations with state tracking and resume support."""

    def __init__(
        self,
        command: str,
        problem_ids: list[int],
        process_fn: Callable[[int], bool],
        *,
        state_dir: Path | None = None,
        filters: BatchFilters | None = None,
        delay: float = 3.0,
        on_progress: Callable[[BatchProgress], None] | None = None,
        dry_run: bool = False,
        resume: bool = False,
    ) -> None:
        """Initialize batch runner.

        Args:
            command: Command name (e.g., "erdos ingest")
            problem_ids: List of problem IDs to process
            process_fn: Function that processes a single problem ID,
                returns True on success, False on failure
            state_dir: Directory for state files (default: logs/)
            filters: Filters used to select problems (for resume validation)
            delay: Seconds between processing each problem
            on_progress: Callback for progress updates
            dry_run: If True, don't actually process
            resume: If True, resume from prior state
        """
        self.command = command
        self.problem_ids = problem_ids
        self.process_fn = process_fn
        self.state_dir = state_dir or Path("logs")
        self.filters = filters or BatchFilters()
        self.delay = delay
        self.on_progress = on_progress
        self.dry_run = dry_run
        self.resume = resume
        self._interrupted = False

    @property
    def batches_dir(self) -> Path:
        """Return the batches subdirectory."""
        return self.state_dir / "batches"

    def run(self) -> BatchResult:
        """Execute the batch operation.

        Returns:
            BatchResult with outcome details
        """
        start_time = datetime.now(tz=UTC)

        # Handle resume
        if self.resume:
            resume_result = self._handle_resume()
            if resume_result is not None:
                return resume_result

        # Create new batch state
        batch_id = generate_batch_id()
        state = BatchState(
            batch_id=batch_id,
            command=self.command,
            filters=self.filters,
            problem_ids=self.problem_ids,
        )

        # Run the batch
        return self._execute_batch(state, start_time)

    def _handle_resume(self) -> BatchResult | None:
        """Handle resume logic. Returns error result if resume fails, else None."""
        # Try to load batch_id from latest.json
        batch_id_result = self._load_latest_batch_id_for_resume()
        if isinstance(batch_id_result, BatchResult):
            return batch_id_result
        batch_id = batch_id_result

        # Try to load prior state
        state_result = self._load_prior_state_for_resume_checked(batch_id)
        if isinstance(state_result, BatchResult):
            return state_result
        prior_state = state_result

        # Validate command matches
        if prior_state.command != self.command:
            return self._error_result(
                f"Command mismatch: prior batch was '{prior_state.command}', "
                f"current is '{self.command}'.",
                ExitCode.USAGE_ERROR,
            )

        # Validate filters match
        if not prior_state.filters.matches(self.filters):
            return self._error_result(
                "Filter mismatch: current filters don't match prior batch.",
                ExitCode.USAGE_ERROR,
            )

        # Update problem_ids to use prior state and continue
        self.problem_ids = prior_state.problem_ids
        return None

    def _load_latest_batch_id_for_resume(self) -> str | BatchResult:
        """Load latest batch ID. Returns batch_id string or error BatchResult."""
        latest_path = self.batches_dir / "latest.json"

        if not latest_path.exists():
            return self._error_result(
                "No previous batch run found. Re-run without --resume.",
                ExitCode.NOT_FOUND,
            )

        try:
            return load_latest_batch_id(latest_path)
        except (json.JSONDecodeError, KeyError) as e:
            return self._error_result(
                f"Corrupted latest.json: {e}. Delete it or re-run without --resume.",
                ExitCode.CONFIG_ERROR,
            )

    def _load_prior_state_for_resume_checked(
        self, batch_id: str
    ) -> BatchState | BatchResult:
        """Load prior batch state. Returns BatchState or error BatchResult."""
        state_path = self.batches_dir / f"{batch_id}.json"

        if not state_path.exists():
            return self._error_result(
                f"Batch state file not found: {state_path}. "
                f"Delete latest.json or re-run without --resume.",
                ExitCode.NOT_FOUND,
            )

        try:
            return load_batch_state(state_path)
        except json.JSONDecodeError as e:
            return self._error_result(
                f"Corrupted batch state file {state_path}: {e}",
                ExitCode.CONFIG_ERROR,
            )
        except ValueError as e:
            return self._error_result(str(e), ExitCode.CONFIG_ERROR)

    def _execute_batch(self, state: BatchState, start_time: datetime) -> BatchResult:
        """Execute the batch processing loop."""
        # Handle dry run
        if self.dry_run:
            duration_ms = int(
                (datetime.now(tz=UTC) - start_time).total_seconds() * 1000
            )
            return BatchResult(
                batch_id=state.batch_id,
                total=len(self.problem_ids),
                completed_count=0,
                failed_count=0,
                failed_ids=[],
                duration_ms=duration_ms,
                dry_run=True,
            )

        # Load prior state if resuming
        if self.resume:
            prior_state = self._load_prior_state_for_resume()
            if prior_state is not None:
                state = prior_state

        # Ensure batches dir exists
        self.batches_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiter for API calls
        limiter = RateLimiter(delay_seconds=self.delay)

        # Process each problem
        total = len(state.problem_ids)
        to_process = state.failed + state.pending  # Retry failed, then pending

        for i, problem_id in enumerate(to_process):
            if self._interrupted:
                break

            # Rate limit
            limiter.sleep_if_needed()

            # Process
            try:
                success = self.process_fn(problem_id)
                if success:
                    state.mark_completed(problem_id)
                    message = "OK"
                else:
                    state.mark_failed(problem_id)
                    message = "Failed"
            except Exception as e:
                logger.exception("Error processing problem %d", problem_id)
                state.mark_failed(problem_id)
                success = False
                message = str(e)

            # Progress callback
            if self.on_progress:
                self.on_progress(
                    BatchProgress(
                        problem_id=problem_id,
                        index=i,
                        total=total,
                        success=success,
                        message=message,
                    )
                )

            # Save state after each problem
            state_path = self.batches_dir / f"{state.batch_id}.json"
            save_batch_state(state_path, state)
            save_latest_batch_id(self.batches_dir / "latest.json", state.batch_id)

        # Calculate result
        duration_ms = int((datetime.now(tz=UTC) - start_time).total_seconds() * 1000)
        return BatchResult(
            batch_id=state.batch_id,
            total=total,
            completed_count=len(state.completed),
            failed_count=len(state.failed),
            failed_ids=state.failed.copy(),
            duration_ms=duration_ms,
        )

    def _load_prior_state_for_resume(self) -> BatchState | None:
        """Load prior state for resume. Returns None if not found."""
        try:
            latest_path = self.batches_dir / "latest.json"
            batch_id = load_latest_batch_id(latest_path)
            state_path = self.batches_dir / f"{batch_id}.json"
            return load_batch_state(state_path)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

    def _error_result(self, message: str, exit_code: ExitCode) -> BatchResult:
        """Create an error BatchResult."""
        return BatchResult(
            batch_id="",
            total=len(self.problem_ids),
            completed_count=0,
            failed_count=0,
            failed_ids=[],
            duration_ms=0,
            exit_code=exit_code,
            error_message=message,
        )

    def interrupt(self) -> None:
        """Signal the runner to stop after the current problem."""
        self._interrupted = True
