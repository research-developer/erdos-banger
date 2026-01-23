from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from erdos.core.research.note import append_scratchpad_entry
from erdos.core.research.workspace import ensure_problem_workspace


def test_workspace_init_is_idempotent(tmp_path: Path) -> None:
    first = ensure_problem_workspace(6, repo_root=tmp_path)
    assert first.created is True
    readme = (tmp_path / "research" / "problems" / "0006" / "README.md").read_text(
        encoding="utf-8"
    )

    second = ensure_problem_workspace(6, repo_root=tmp_path)
    assert second.created is False
    readme_after = (
        tmp_path / "research" / "problems" / "0006" / "README.md"
    ).read_text(encoding="utf-8")
    assert readme_after == readme


def test_note_appends_without_rewriting(tmp_path: Path) -> None:
    ensure_problem_workspace(6, repo_root=tmp_path)

    t1 = datetime(2026, 1, 23, 0, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 23, 0, 1, 0, tzinfo=UTC)

    append_scratchpad_entry(6, "first", repo_root=tmp_path, now=t1)
    append_scratchpad_entry(6, "second", repo_root=tmp_path, now=t2)

    text = (tmp_path / "research" / "problems" / "0006" / "SCRATCHPAD.md").read_text(
        encoding="utf-8"
    )
    assert "first" in text
    assert "second" in text
    assert "## 2026-01-23T00:00:00Z" in text
    assert "## 2026-01-23T00:01:00Z" in text
