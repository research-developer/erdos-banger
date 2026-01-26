"""Ask logging utilities.

Persists full LLM Q&A interactions to `logs/ask/problem_{id}.jsonl`.
Design mirrors `erdos.core.loop.logging` for consistency (DEBT-113).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _get_default_log_dir() -> Path:
    """Get default ask log directory (logs/ask/)."""
    return Path("logs/ask")


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
    log_path = log_dir / f"problem_{problem_id}.jsonl"

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
                "source_type": s.get("source_type"),
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

    # Append to file
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return log_path
