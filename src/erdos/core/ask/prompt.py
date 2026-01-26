"""Prompt construction for RAG Q&A."""

from __future__ import annotations

import codecs
from typing import TYPE_CHECKING

from erdos.core.constants import ASK_PROMPT_MAX_BYTES


if TYPE_CHECKING:
    from erdos.core.models import ProblemRecord
    from erdos.core.search.types import SearchResult


_TRUNCATION_MARKER = "\n(...truncated...)"

_MIN_STATEMENT_BYTES = 128
_MIN_QUESTION_BYTES = 128
_MAX_NOTES_BYTES = 2048


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _truncate_utf8_bytes(text: str, *, max_bytes: int) -> str:
    """Truncate a string to a max UTF-8 byte length, appending a marker when cut.

    This implementation avoids encoding the full input when the text is obviously
    larger than the budget (since UTF-8 uses >= 1 byte per codepoint).
    """
    if max_bytes <= 0:
        return ""

    # Fast path: when the string is short enough in codepoints, we can cheaply
    # validate whether it fits in UTF-8 bytes.
    if len(text) <= max_bytes and _utf8_len(text) <= max_bytes:
        return text

    marker_bytes = _TRUNCATION_MARKER.encode("utf-8")
    if max_bytes <= len(marker_bytes):
        return marker_bytes[:max_bytes].decode("utf-8", errors="ignore")

    content_budget = max_bytes - len(marker_bytes)
    encoder = codecs.getincrementalencoder("utf-8")()
    out = bytearray()

    for ch in text:
        encoded = encoder.encode(ch)
        if len(out) + len(encoded) > content_budget:
            break
        out.extend(encoded)

    prefix = out.decode("utf-8", errors="ignore")
    return prefix + _TRUNCATION_MARKER


def _build_sections(
    *,
    problem: ProblemRecord,
    sources: list[SearchResult],
    statement_text: str,
    notes_text: str,
    source_texts: list[str],
    question_text: str,
) -> list[str]:
    sections: list[str] = []

    # Header
    sections.append("You are assisting with research on a specific Erdős problem.")
    sections.append("")

    # Problem metadata
    sections.append("Problem:")
    sections.append(f"- id: {problem.id}")
    sections.append(f"- title: {problem.title}")
    sections.append("")

    # Statement
    sections.append("Statement:")
    sections.append(statement_text)
    sections.append("")

    # Notes section
    sections.append("Notes:")
    sections.append(notes_text)
    sections.append("")

    # Sources
    sections.append("Sources (cite as [n]):")
    if sources:
        for idx, source in enumerate(sources, start=1):
            sections.append(f"[{idx}] ({source.source_type.value}) {source.chunk_id}")
            sections.append(source_texts[idx - 1])
            sections.append("")
    else:
        sections.append("(no sources retrieved)")
        sections.append("")

    # Question
    sections.append("Question:")
    sections.append(question_text)
    sections.append("")

    # Instructions
    sections.append("Instructions:")
    sections.append("- Answer using only the sources above.")
    sections.append(
        "- When making a claim, cite the supporting source like [1] or [2]."
    )
    sections.append(
        "- If the sources are insufficient, say so explicitly and suggest what to ingest/search next."
    )

    return sections


def _budget_prompt(
    problem: ProblemRecord,
    sources: list[SearchResult],
    question: str,
    *,
    max_bytes: int,
) -> str:
    # Compute the byte overhead of the fixed prompt scaffold (all variable texts empty).
    notes_has_content = bool(problem.notes)
    overhead_sections = _build_sections(
        problem=problem,
        sources=sources,
        statement_text="",
        notes_text="" if notes_has_content else "(none)",
        source_texts=["" for _ in sources],
        question_text="",
    )
    overhead_bytes = _utf8_len("\n".join(overhead_sections))

    if max_bytes <= overhead_bytes:
        # Extremely small budget: return the scaffold truncated hard (best-effort).
        scaffold = "\n".join(overhead_sections)
        return _truncate_utf8_bytes(scaffold, max_bytes=max_bytes)

    available = max_bytes - overhead_bytes

    statement = problem.statement
    notes = problem.notes or ""

    statement_budget = min(_utf8_len(statement), available)
    available -= statement_budget

    question_budget = min(_utf8_len(question), available)
    available -= question_budget

    # Ensure statement/question are not accidentally budgeted down to empty when possible.
    question_len = _utf8_len(question) if question else 0
    statement_len = _utf8_len(statement) if statement else 0

    if question and question_budget < min(question_len, _MIN_QUESTION_BYTES):
        need = min(question_len, _MIN_QUESTION_BYTES) - question_budget
        take = min(need, statement_budget)
        statement_budget -= take
        question_budget += take

    if statement and statement_budget < min(statement_len, _MIN_STATEMENT_BYTES):
        need = min(statement_len, _MIN_STATEMENT_BYTES) - statement_budget
        take = min(need, question_budget)
        question_budget -= take
        statement_budget += take

    notes_budget = 0
    if notes_has_content and available > 0:
        notes_budget = min(_utf8_len(notes), available, _MAX_NOTES_BYTES)
        available -= notes_budget

    source_budgets: list[int] = []
    if sources and available > 0:
        base = available // len(sources)
        extra = available % len(sources)
        for i in range(len(sources)):
            source_budgets.append(base + (1 if i < extra else 0))
    else:
        source_budgets = [0 for _ in sources]

    statement_text = _truncate_utf8_bytes(statement, max_bytes=statement_budget)
    question_text = _truncate_utf8_bytes(question, max_bytes=question_budget)
    notes_text = (
        _truncate_utf8_bytes(notes, max_bytes=notes_budget)
        if notes_has_content
        else "(none)"
    )

    source_texts: list[str] = []
    for source, budget in zip(sources, source_budgets, strict=True):
        source_texts.append(_truncate_utf8_bytes(source.text, max_bytes=budget))

    sections = _build_sections(
        problem=problem,
        sources=sources,
        statement_text=statement_text,
        notes_text=notes_text,
        source_texts=source_texts,
        question_text=question_text,
    )
    return "\n".join(sections)


def build_prompt(
    problem: ProblemRecord,
    sources: list[SearchResult],
    question: str,
    *,
    max_bytes: int = ASK_PROMPT_MAX_BYTES,
) -> str:
    """
    Build a deterministic RAG prompt.

    Args:
        problem: The problem record
        sources: Retrieved text chunks (ordered by relevance)
        question: User's question
        max_bytes: Hard cap for the prompt size in UTF-8 bytes.

    Returns:
        Formatted prompt string
    """
    prompt = _budget_prompt(problem, sources, question, max_bytes=max_bytes)
    # Defensive assertion: budgeting should guarantee the cap.
    if max_bytes > 0 and _utf8_len(prompt) > max_bytes:
        return _truncate_utf8_bytes(prompt, max_bytes=max_bytes)
    return prompt
