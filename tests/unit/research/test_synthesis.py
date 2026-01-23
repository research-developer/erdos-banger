from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from erdos.core.research.models import (
    AttemptResult,
    HypothesisStatus,
    LeadStatus,
    Priority,
)
from erdos.core.research.note import append_scratchpad_entry
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.synthesis import synthesize_problem
from erdos.core.research.workspace import ensure_problem_workspace


def test_synthesize_problem_is_deterministic(tmp_path: Path) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)
    store = FSResearchStore(repo_root=tmp_path)

    # Tasks: high priority first, then created_at asc within priority.
    t0 = datetime(2026, 1, 23, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 23, 0, 1, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 23, 0, 2, 0, tzinfo=UTC)

    store.task_add(6, title="Task A", priority=Priority.HIGH, now=t2)
    store.task_add(6, title="Task B", priority=Priority.HIGH, now=t1)
    store.task_add(6, title="Task C", priority=Priority.LOW, now=t0)

    # Hypotheses: only active are included.
    store.hypothesis_add(
        6, statement="Active hyp", status=HypothesisStatus.ACTIVE, now=t0
    )
    store.hypothesis_add(
        6, statement="Refuted hyp", status=HypothesisStatus.REFUTED, now=t0
    )

    # Leads: exclude dead_end and incorporated.
    store.lead_add(
        6,
        title="Lead 1",
        status=LeadStatus.INVESTIGATING,
        priority=Priority.MEDIUM,
        now=t0,
    )
    store.lead_add(
        6, title="Lead 2", status=LeadStatus.DEAD_END, priority=Priority.HIGH, now=t0
    )
    store.lead_add(
        6, title="Lead 3", status=LeadStatus.PROMISING, priority=Priority.HIGH, now=t1
    )

    # Attempts: most recent first.
    store.attempt_log(6, result=AttemptResult.FAILED, summary="Attempt old", now=t0)
    store.attempt_log(6, result=AttemptResult.SUCCESS, summary="Attempt new", now=t2)

    # Scratchpad entries
    append_scratchpad_entry(6, "first note", repo_root=tmp_path, now=t0)
    append_scratchpad_entry(6, "second note", repo_root=tmp_path, now=t1)

    res = synthesize_problem(
        6, repo_root=tmp_path, now=datetime(2026, 1, 23, 12, 0, 0, tzinfo=UTC)
    )
    assert res.problem_id == 6

    text = (tmp_path / "research" / "problems" / "0006" / "SYNTHESIS.md").read_text(
        encoding="utf-8"
    )
    assert "# Synthesis: Problem 0006" in text
    assert "_Last updated: 2026-01-23_" in text

    # Tasks: Task B (older) should appear before Task A within HIGH priority.
    assert text.index("Task B") < text.index("Task A")
    assert text.index("Task A") < text.index("Task C")

    # Hypotheses: only active
    assert "Active hyp" in text
    assert "Refuted hyp" not in text

    # Leads: Lead 3 (high) should appear before Lead 1 (medium); Lead 2 excluded.
    assert "Lead 3" in text
    assert "Lead 1" in text
    assert "Lead 2" not in text
    assert text.index("Lead 3") < text.index("Lead 1")

    # Attempts: new before old
    assert text.index("Attempt new") < text.index("Attempt old")

    # Notes include excerpts
    assert "first note" in text
    assert "second note" in text
