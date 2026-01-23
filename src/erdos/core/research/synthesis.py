"""Deterministic research synthesis (Spec 026)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from erdos.core.research.models import HypothesisStatus, LeadStatus, Priority
from erdos.core.research.paths import get_problem_dir
from erdos.core.research.store_fs import FSResearchStore
from erdos.core.research.workspace import ensure_problem_workspace
from erdos.core.research.yaml_io import write_text_atomic


if TYPE_CHECKING:
    from pathlib import Path


def _utc_now(now: datetime | None = None) -> datetime:
    dt = now if now is not None else datetime.now(UTC)
    return dt.replace(microsecond=0)


def _priority_score(priority: Priority) -> int:
    return {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}[priority]


def _extract_recent_scratchpad_entries(
    scratchpad_text: str, *, limit: int
) -> list[tuple[str, str]]:
    """Return (timestamp, excerpt) tuples for recent scratchpad entries."""
    parts = scratchpad_text.split("\n## ")
    if len(parts) <= 1:
        return []

    entries: list[tuple[str, str]] = []
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        ts = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        excerpt = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        entries.append((ts, excerpt))
    return entries[-limit:]


def _section(title: str, bullets: list[str]) -> list[str]:
    body = bullets if bullets else ["- (none)"]
    return [title, *body, ""]


@dataclass(frozen=True)
class SynthesisResult:
    problem_id: int
    synthesis_path: Path
    written_bytes: int
    counts: dict[str, int]


def synthesize_problem(
    problem_id: int, *, repo_root: Path | None, now: datetime | None = None
) -> SynthesisResult:
    """Generate/overwrite `SYNTHESIS.md` deterministically (no LLM)."""
    ensure_problem_workspace(problem_id, repo_root=repo_root)
    store = FSResearchStore(repo_root=repo_root)
    problem_dir = get_problem_dir(repo_root, problem_id)

    scratchpad_path = problem_dir / "SCRATCHPAD.md"
    scratchpad_text = (
        scratchpad_path.read_text(encoding="utf-8") if scratchpad_path.exists() else ""
    )

    tasks = store.task_list(problem_id)
    hypotheses = store.hypothesis_list(problem_id)
    leads = store.lead_list(problem_id)
    attempts = store.attempt_list(problem_id)

    tasks_sorted = sorted(
        tasks, key=lambda t: (-_priority_score(t.priority), t.created_at)
    )[:10]
    active_hypotheses = [h for h in hypotheses if h.status == HypothesisStatus.ACTIVE]
    active_hypotheses_sorted = sorted(active_hypotheses, key=lambda h: h.created_at)[
        :10
    ]
    key_leads = [
        lead
        for lead in leads
        if lead.status not in (LeadStatus.DEAD_END, LeadStatus.INCORPORATED)
    ]
    key_leads_sorted = sorted(
        key_leads,
        key=lambda lead: (
            -_priority_score(lead.priority),
            -lead.updated_at.timestamp(),
        ),
    )[:10]
    attempts_sorted = sorted(attempts, key=lambda a: a.created_at, reverse=True)[:5]
    notes = _extract_recent_scratchpad_entries(scratchpad_text, limit=5)

    if not tasks and not hypotheses and not leads and not attempts and not notes:
        summary_line = "- No recorded leads, tasks, hypotheses, attempts, or notes yet."
    else:
        summary_line = (
            f"- {len(tasks)} tasks, {len(active_hypotheses)} active hypotheses, "
            f"{len(key_leads)} key leads, {len(attempts)} attempts."
        )

    last_updated = _utc_now(now).date().isoformat()

    lines: list[str] = [
        f"# Synthesis: Problem {problem_id:04d}",
        f"_Last updated: {last_updated}_",
        "",
        "## Summary",
        summary_line,
        "",
        *_section(
            "## Top tasks (by priority)",
            [
                f"- [{t.status.value}] ({t.priority.value}) {t.title}"
                for t in tasks_sorted
            ],
        ),
        *_section(
            "## Active hypotheses",
            [
                f"- ({h.confidence.value}) {h.statement}"
                for h in active_hypotheses_sorted
            ],
        ),
        *_section(
            "## Key leads (by priority)",
            [
                f"- [{lead.status.value}] ({lead.priority.value}) {lead.title}"
                for lead in key_leads_sorted
            ],
        ),
        *_section(
            "## Recent attempts (most recent first)",
            [
                f"- [{a.result.value}] ({a.kind.value}) {a.summary}"
                for a in attempts_sorted
            ],
        ),
        *_section(
            "## Notes (recent scratchpad excerpts)",
            [f"- {ts}: {excerpt or '(empty)'}" for ts, excerpt in notes],
        ),
    ]

    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"

    synthesis_path = problem_dir / "SYNTHESIS.md"
    old = synthesis_path.read_text(encoding="utf-8") if synthesis_path.exists() else ""
    if old == content:
        written_bytes = 0
    else:
        write_text_atomic(synthesis_path, content)
        written_bytes = len(content.encode("utf-8"))

    return SynthesisResult(
        problem_id=problem_id,
        synthesis_path=synthesis_path,
        written_bytes=written_bytes,
        counts={
            "tasks": len(tasks),
            "hypotheses": len(active_hypotheses),
            "leads": len(key_leads),
            "attempts": len(attempts),
        },
    )
