"""Prompt construction for RAG Q&A."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _PromptBudgets:
    statement: int
    question: int
    notes: int
    sources_total: int


def _prompt_overhead(
    problem: ProblemRecord, sources: list[SearchResult]
) -> tuple[int, list[str], bool]:
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
    return overhead_bytes, overhead_sections, notes_has_content


def _top_up_budget(*, available: int, current: int, max_len: int) -> tuple[int, int]:
    if available <= 0 or current >= max_len:
        return available, current
    take = min(available, max_len - current)
    return available - take, current + take


def _ensure_min_statement_budget(
    budgets: _PromptBudgets,
    *,
    statement_len: int,
) -> _PromptBudgets:
    if statement_len <= 0:
        return budgets
    minimum = min(statement_len, _MIN_STATEMENT_BYTES)
    if budgets.statement >= minimum:
        return budgets

    need = minimum - budgets.statement

    take_from_notes = min(need, budgets.notes)
    need -= take_from_notes
    notes_budget = budgets.notes - take_from_notes
    statement_budget = budgets.statement + take_from_notes

    take_from_sources = min(need, budgets.sources_total)
    need -= take_from_sources
    statement_budget += take_from_sources
    sources_budget = budgets.sources_total - take_from_sources

    question_budget = budgets.question
    if need > 0 and question_budget > 0:
        take_from_question = min(need, question_budget)
        question_budget -= take_from_question
        statement_budget += take_from_question
        need -= take_from_question

    return _PromptBudgets(
        statement=statement_budget,
        question=question_budget,
        notes=notes_budget,
        sources_total=sources_budget,
    )


def _allocate_prompt_budgets(
    *,
    max_bytes: int,
    overhead_bytes: int,
    question_len: int,
    statement_len: int,
    notes_len: int,
    sources_len_total: int,
    notes_has_content: bool,
    has_sources: bool,
) -> _PromptBudgets:
    available = max(0, max_bytes - overhead_bytes)

    question_budget = min(question_len, available)
    available -= question_budget

    notes_budget = 0
    if notes_has_content and available > 0:
        notes_target = available // 5  # ~20% of remaining budget
        notes_budget = min(notes_len, notes_target)
        available -= notes_budget

    sources_budget_total = 0
    if has_sources and available > 0:
        sources_target = available // 2
        sources_budget_total = min(sources_len_total, sources_target)
        available -= sources_budget_total

    statement_budget = min(statement_len, available)
    available -= statement_budget

    available, sources_budget_total = _top_up_budget(
        available=available, current=sources_budget_total, max_len=sources_len_total
    )
    available, notes_budget = _top_up_budget(
        available=available, current=notes_budget, max_len=notes_len
    )
    available, statement_budget = _top_up_budget(
        available=available, current=statement_budget, max_len=statement_len
    )

    budgets = _PromptBudgets(
        statement=statement_budget,
        question=question_budget,
        notes=notes_budget,
        sources_total=sources_budget_total,
    )
    return _ensure_min_statement_budget(budgets, statement_len=statement_len)


def _split_even_budget(total: int, n: int) -> list[int]:
    if n <= 0:
        return []
    if total <= 0:
        return [0 for _ in range(n)]
    base, extra = divmod(total, n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def _budget_prompt(
    problem: ProblemRecord,
    sources: list[SearchResult],
    question: str,
    *,
    max_bytes: int,
) -> str:
    overhead_bytes, overhead_sections, notes_has_content = _prompt_overhead(
        problem, sources
    )

    if max_bytes <= overhead_bytes:
        # Extremely small budget: return the scaffold truncated hard (best-effort).
        scaffold = "\n".join(overhead_sections)
        return _truncate_utf8_bytes(scaffold, max_bytes=max_bytes)

    statement = problem.statement
    notes = problem.notes or ""

    # Effective sizes (note: we cap notes by design to avoid flooding the prompt).
    question_len = _utf8_len(question) if question else 0
    statement_len = _utf8_len(statement) if statement else 0
    notes_len = min(_utf8_len(notes), _MAX_NOTES_BYTES) if notes_has_content else 0
    source_lens = [_utf8_len(source.text) for source in sources]
    sources_len_total = sum(source_lens)

    budgets = _allocate_prompt_budgets(
        max_bytes=max_bytes,
        overhead_bytes=overhead_bytes,
        question_len=question_len,
        statement_len=statement_len,
        notes_len=notes_len,
        sources_len_total=sources_len_total,
        notes_has_content=notes_has_content,
        has_sources=bool(sources),
    )
    if budgets.sources_total >= sources_len_total:
        # We have enough total budget to include all sources; keep per-source budgets
        # large enough to avoid truncation (important for determinism in tests).
        source_budgets = source_lens
    else:
        source_budgets = _split_even_budget(budgets.sources_total, len(sources))

    statement_text = _truncate_utf8_bytes(statement, max_bytes=budgets.statement)
    question_text = _truncate_utf8_bytes(question, max_bytes=budgets.question)
    notes_text = (
        _truncate_utf8_bytes(notes, max_bytes=budgets.notes)
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
