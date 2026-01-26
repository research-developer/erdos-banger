"""Ask logging utilities.

Persists full LLM Q&A interactions to `logs/ask/problem_{id}.jsonl`.
Design mirrors `erdos.core.loop.logging` for consistency (DEBT-113).
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ConfigDict, Field, ValidationError

from erdos.core.models.base import ErdosBaseModel
from erdos.core.run_logger import sanitize_secrets


logger = logging.getLogger(__name__)


class AskLogSource(ErdosBaseModel):
    """A logged retrieval source (metadata only)."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="allow",
    )

    chunk_id: str | None = None
    source_type: str | None = None
    reference_doi: str | None = None
    rank: int | None = None
    problem_id: int | None = None


class AskLogLLM(ErdosBaseModel):
    """Logged LLM invocation metadata."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="allow",
    )

    enabled: bool = False
    command: str | None = None
    exit_code: int | None = None


class AskLogEntry(ErdosBaseModel):
    """A single `erdos ask` interaction log entry."""

    model_config = ConfigDict(
        frozen=False,
        strict=False,
        extra="allow",
    )

    schema_version: int = Field(default=1)
    timestamp: datetime
    problem_id: int
    question: str
    answer: str | None = None
    source_count: int = 0
    sources: list[AskLogSource] = Field(default_factory=list)
    llm: AskLogLLM = Field(default_factory=AskLogLLM)


def _get_default_log_dir() -> Path:
    """Get default ask log directory (logs/ask/)."""
    return Path("logs/ask")


def get_ask_log_path(problem_id: int, *, log_dir: Path | None = None) -> Path:
    """Return the per-problem ask log path."""
    log_dir = log_dir or _get_default_log_dir()
    return log_dir / f"problem_{problem_id}.jsonl"


def read_ask_log_entries(
    problem_id: int,
    *,
    limit: int = 50,
    since: datetime | None = None,
    log_dir: Path | None = None,
) -> tuple[list[AskLogEntry], int, Path]:
    """Read the most recent ask log entries for a problem.

    Args:
        problem_id: Problem ID to read.
        limit: Maximum number of entries to return (most recent).
        since: Optional timestamp filter.
        log_dir: Optional log directory override.

    Returns:
        (entries, parse_errors, log_path)
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")

    log_path = get_ask_log_path(problem_id, log_dir=log_dir)
    if not log_path.exists():
        return [], 0, log_path

    parse_errors = 0
    entries: deque[AskLogEntry] = deque(maxlen=limit)

    with log_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue

            try:
                entry = AskLogEntry.model_validate(payload)
            except ValidationError:
                parse_errors += 1
                continue

            if since is not None and entry.timestamp < since:
                continue

            entries.append(entry)

    return list(entries), parse_errors, log_path


def log_ask_interaction(
    problem_id: int,
    *,
    question: str,
    answer: str | None,
    sources: list[dict[str, Any]],
    llm_enabled: bool,
    llm_command: str | None = None,
    llm_exit_code: int | None = None,
    log_dir: Path | None = None,
) -> Path:
    """Log an ask Q&A interaction to per-problem JSONL file.

    Args:
        problem_id: The problem ID.
        question: The user's question.
        answer: The LLM's answer (None if LLM disabled).
        sources: Retrieved sources (chunk metadata, not full text).
        llm_enabled: Whether LLM was used.
        llm_command: The LLM command executed.
        llm_exit_code: Exit code from LLM execution.
        log_dir: Optional log directory override.

    Returns:
        Path to the log file where the interaction was written.
    """
    log_dir = log_dir or _get_default_log_dir()
    log_path = get_ask_log_path(problem_id, log_dir=log_dir)

    # Ensure directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Build log entry
    entry = {
        "schema_version": 1,
        "timestamp": datetime.now(UTC).isoformat(),
        "problem_id": problem_id,
        "question": question,
        "answer": answer,
        "source_count": len(sources),
        "sources": [
            {
                "chunk_id": s.get("chunk_id"),
                "rank": s.get("rank"),
                "source_type": s.get("source_type"),
                "problem_id": s.get("problem_id"),
                "reference_doi": s.get("reference_doi"),
            }
            for s in sources
        ],
        "llm": {
            "enabled": llm_enabled,
            "command": llm_command,
            "exit_code": llm_exit_code,
        },
    }
    entry = sanitize_secrets(entry)

    # Append to file
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()

    return log_path
