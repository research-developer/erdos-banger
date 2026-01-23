"""Scratchpad note writing (Spec 023)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

from erdos.core.research.paths import get_problem_dir
from erdos.core.research.time import utc_now_iso_z
from erdos.core.research.workspace import ensure_problem_workspace


@dataclass(frozen=True)
class AppendNoteResult:
    problem_id: int
    scratchpad_path: Path
    appended_bytes: int


def append_scratchpad_entry(
    problem_id: int,
    text: str,
    *,
    repo_root: Path | None,
    now: datetime | None = None,
) -> AppendNoteResult:
    """Append a timestamped entry to the per-problem scratchpad."""
    ensure_problem_workspace(problem_id, repo_root=repo_root)
    scratchpad_path = get_problem_dir(repo_root, problem_id) / "SCRATCHPAD.md"

    entry = f"\n## {utc_now_iso_z(now)}\n\n{text.rstrip()}\n"
    encoded = entry.encode("utf-8")
    with scratchpad_path.open("a", encoding="utf-8") as f:
        f.write(entry)
    return AppendNoteResult(
        problem_id=problem_id,
        scratchpad_path=scratchpad_path,
        appended_bytes=len(encoded),
    )
