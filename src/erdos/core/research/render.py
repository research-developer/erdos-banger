"""Deterministic renderers for research records (Spec 025)."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.research.models import (
        AttemptRecord,
        HypothesisRecord,
        LeadRecord,
        TaskRecord,
    )


def render_lead(record: LeadRecord) -> str:
    src = record.source
    return (
        "Kind: lead\n"
        f"ID: {record.id}\n"
        f"Problem: {record.problem_id}\n"
        f"Title: {record.title}\n"
        f"Status: {record.status.value}\n"
        f"Priority: {record.priority.value}\n"
        f"Source: doi={src.doi or ''} arxiv_id={src.arxiv_id or ''} url={src.url or ''}\n"
        "Notes:\n"
        f"{record.notes}\n"
    )


def render_attempt(record: AttemptRecord) -> str:
    a = record.artifacts
    return (
        "Kind: attempt\n"
        f"ID: {record.id}\n"
        f"Problem: {record.problem_id}\n"
        f"AttemptKind: {record.kind.value}\n"
        f"Result: {record.result.value}\n"
        "Summary:\n"
        f"{record.summary}\n"
        "Artifacts:\n"
        f"- lean_file: {a.lean_file or ''}\n"
        f"- loop_run_log: {a.loop_run_log or ''}\n"
    )


def render_hypothesis(record: HypothesisRecord) -> str:
    evidence = ", ".join(record.evidence)
    return (
        "Kind: hypothesis\n"
        f"ID: {record.id}\n"
        f"Problem: {record.problem_id}\n"
        f"Status: {record.status.value}\n"
        f"Confidence: {record.confidence.value}\n"
        "Statement:\n"
        f"{record.statement}\n"
        f"Evidence: {evidence}\n"
        "Notes:\n"
        f"{record.notes}\n"
    )


def render_task(record: TaskRecord) -> str:
    blocked_on = ", ".join(record.blocked_on)
    links = ", ".join(record.links)
    return (
        "Kind: task\n"
        f"ID: {record.id}\n"
        f"Problem: {record.problem_id}\n"
        f"Title: {record.title}\n"
        f"Status: {record.status.value}\n"
        f"Priority: {record.priority.value}\n"
        f"BlockedOn: {blocked_on}\n"
        f"Links: {links}\n"
    )
