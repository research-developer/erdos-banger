"""Dashboard data aggregation (SPEC-034).

Aggregates research workspace data for dashboard display.
Primary data source: research/problems/<id>/ (filesystem SSOT).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from erdos.core.research.models import (
    AttemptResult,
    HypothesisStatus,
    LeadStatus,
    TaskStatus,
)
from erdos.core.research.store_fs import FSResearchStore


if TYPE_CHECKING:
    from pathlib import Path

    from erdos.core.research.models import (
        AttemptRecord,
        HypothesisRecord,
        LeadRecord,
        TaskRecord,
    )


_logger = logging.getLogger(__name__)


# Status thresholds (days since last activity)
_STALE_THRESHOLD_DAYS = 14


def _is_lead_active(status: LeadStatus) -> bool:
    """Lead is active if not DEAD_END or INCORPORATED."""
    return status not in (LeadStatus.DEAD_END, LeadStatus.INCORPORATED)


def _is_hypothesis_active(status: HypothesisStatus) -> bool:
    """Hypothesis is active only if status is ACTIVE."""
    return status == HypothesisStatus.ACTIVE


def _is_task_open(status: TaskStatus) -> bool:
    """Task is open if not DONE."""
    return status != TaskStatus.DONE


def _get_latest_activity(
    leads: list[LeadRecord],
    hypotheses: list[HypothesisRecord],
    tasks: list[TaskRecord],
    attempts: list[AttemptRecord],
) -> datetime | None:
    """Get the most recent activity timestamp from all records."""
    timestamps: list[datetime] = []

    for lead in leads:
        timestamps.append(lead.updated_at)
    for hyp in hypotheses:
        timestamps.append(hyp.updated_at)
    for task in tasks:
        timestamps.append(task.updated_at)
    for attempt in attempts:
        timestamps.append(attempt.created_at)

    return max(timestamps) if timestamps else None


def _compute_problem_status(last_activity: datetime | None, now: datetime) -> str:
    """Compute problem status based on activity recency."""
    if last_activity is None:
        return "new"

    days_since = (now - last_activity).days
    if days_since <= _STALE_THRESHOLD_DAYS:
        return "active"
    return "stale"


@dataclass
class ProblemStats:
    """Statistics for a single problem."""

    problem_id: int
    status: str  # "new", "active", "stale"
    lead_count: int
    hypothesis_count: int
    task_count: int
    attempt_count: int
    success_count: int
    last_activity: datetime | None

    @property
    def success_rate(self) -> float | None:
        """Success rate as percentage, None if no attempts."""
        if self.attempt_count == 0:
            return None
        return (self.success_count / self.attempt_count) * 100.0

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict."""
        return {
            "problem_id": self.problem_id,
            "status": self.status,
            "lead_count": self.lead_count,
            "hypothesis_count": self.hypothesis_count,
            "task_count": self.task_count,
            "attempt_count": self.attempt_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
        }


@dataclass
class DashboardData:
    """Aggregated dashboard data across all problems."""

    problems: list[ProblemStats]
    total_attempts: int
    total_successes: int
    active_leads: int
    active_hypotheses: int
    open_tasks: int
    attempt_timeline: dict[str, list[str]]  # date str -> list of result values
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def overall_success_rate(self) -> float | None:
        """Overall success rate as percentage, None if no attempts."""
        if self.total_attempts == 0:
            return None
        return (self.total_successes / self.total_attempts) * 100.0

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict for CLIOutput."""
        return {
            "problems": [p.to_dict() for p in self.problems],
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "overall_success_rate": self.overall_success_rate,
            "active_leads": self.active_leads,
            "active_hypotheses": self.active_hypotheses,
            "open_tasks": self.open_tasks,
            "attempt_timeline": self.attempt_timeline,
            "generated_at": self.generated_at.isoformat(),
        }


def _discover_problem_ids(research_path: Path) -> list[int]:
    """Discover all problem IDs from the research workspace."""
    problems_dir = research_path / "problems"
    if not problems_dir.exists():
        return []

    problem_ids: list[int] = []
    for entry in problems_dir.iterdir():
        if entry.is_dir() and entry.name.isdigit():
            problem_ids.append(int(entry.name))
    return sorted(problem_ids)


def _aggregate_problem(
    store: FSResearchStore,
    problem_id: int,
    now: datetime,
) -> tuple[ProblemStats, list[AttemptRecord]]:
    """Aggregate stats for a single problem."""
    leads = store.lead_list(problem_id)
    hypotheses = store.hypothesis_list(problem_id)
    tasks = store.task_list(problem_id)
    attempts = store.attempt_list(problem_id)

    success_count = sum(1 for a in attempts if a.result == AttemptResult.SUCCESS)
    last_activity = _get_latest_activity(leads, hypotheses, tasks, attempts)
    status = _compute_problem_status(last_activity, now)

    stats = ProblemStats(
        problem_id=problem_id,
        status=status,
        lead_count=len(leads),
        hypothesis_count=len(hypotheses),
        task_count=len(tasks),
        attempt_count=len(attempts),
        success_count=success_count,
        last_activity=last_activity,
    )

    return stats, attempts


def aggregate_dashboard_data(
    research_path: Path,
    *,
    problem_ids: list[int] | None = None,
    recent: timedelta = timedelta(days=30),
    now: datetime | None = None,
) -> DashboardData:
    """Aggregate dashboard data from the research workspace.

    Args:
        research_path: Path to the research/ directory.
        problem_ids: Optional list of problem IDs to include.
            If None, includes all discovered problems.
        recent: Time window for attempt timeline (default 30 days).
        now: Reference time for computing status. Defaults to current time.

    Returns:
        DashboardData with aggregated statistics.
    """
    if now is None:
        now = datetime.now(UTC).replace(microsecond=0)

    # Discover or filter problem IDs
    all_problem_ids = _discover_problem_ids(research_path)
    if problem_ids is not None:
        all_problem_ids = [pid for pid in all_problem_ids if pid in problem_ids]

    # Create store relative to research_path parent (repo root)
    repo_root = research_path.parent
    store = FSResearchStore(repo_root=repo_root)

    # Aggregate each problem
    all_stats: list[ProblemStats] = []
    all_attempts: list[AttemptRecord] = []
    total_active_leads = 0
    total_active_hypotheses = 0
    total_open_tasks = 0

    for pid in all_problem_ids:
        try:
            stats, attempts = _aggregate_problem(store, pid, now)
            all_stats.append(stats)
            all_attempts.extend(attempts)

            # Count active/open items
            leads = store.lead_list(pid)
            hypotheses = store.hypothesis_list(pid)
            tasks = store.task_list(pid)

            total_active_leads += sum(
                1 for lead in leads if _is_lead_active(lead.status)
            )
            total_active_hypotheses += sum(
                1 for h in hypotheses if _is_hypothesis_active(h.status)
            )
            total_open_tasks += sum(1 for t in tasks if _is_task_open(t.status))
        except Exception:
            _logger.debug("Skipping problem %d due to invalid records", pid)
            continue

    # Sort problems by last_activity descending (most recent first)
    # Problems with no activity go to the end
    all_stats.sort(
        key=lambda s: (
            s.last_activity is not None,
            s.last_activity or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )

    # Filter attempts by recent window
    cutoff = now - recent
    recent_attempts = [a for a in all_attempts if a.created_at >= cutoff]

    # Build attempt timeline
    timeline: dict[str, list[str]] = {}
    for attempt in recent_attempts:
        date_str = attempt.created_at.strftime("%Y-%m-%d")
        if date_str not in timeline:
            timeline[date_str] = []
        timeline[date_str].append(attempt.result.value)

    # Compute totals from recent attempts
    total_attempts = len(recent_attempts)
    total_successes = sum(
        1 for a in recent_attempts if a.result == AttemptResult.SUCCESS
    )

    return DashboardData(
        problems=all_stats,
        total_attempts=total_attempts,
        total_successes=total_successes,
        active_leads=total_active_leads,
        active_hypotheses=total_active_hypotheses,
        open_tasks=total_open_tasks,
        attempt_timeline=timeline,
        generated_at=now,
    )
