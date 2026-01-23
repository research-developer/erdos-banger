"""Workspace initialization (Spec 023)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from erdos.core.research.paths import (
    WORKSPACE_VERSION,
    get_problem_dir,
    get_research_root,
)
from erdos.core.research.time import utc_now_iso_z


if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


def _write_text_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_yaml_if_missing(path: Path, data: dict[str, object]) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return True


@dataclass(frozen=True)
class WorkspaceInitResult:
    problem_id: int
    research_root: Path
    problem_dir: Path
    created_paths: tuple[str, ...]
    workspace_version: int = WORKSPACE_VERSION

    @property
    def created(self) -> bool:
        return bool(self.created_paths)


def ensure_problem_workspace(
    problem_id: int, *, repo_root: Path | None, now: datetime | None = None
) -> WorkspaceInitResult:
    """Create the research workspace for a problem if missing.

    Idempotent: never overwrites existing files.
    """
    research_root = get_research_root(repo_root)
    problem_dir = get_problem_dir(repo_root, problem_id)

    created: list[str] = []

    # Workspace root and version
    version_path = research_root / "VERSION"
    if _write_text_if_missing(version_path, f"{WORKSPACE_VERSION}\n"):
        created.append("research/VERSION")

    # Global stubs
    techniques_path = research_root / "global" / "TECHNIQUES.md"
    if _write_text_if_missing(
        techniques_path,
        "# Techniques\n\n"
        "Reusable proof techniques, patterns, and Lean tactics discovered during research.\n",
    ):
        created.append("research/global/TECHNIQUES.md")

    glossary_path = research_root / "global" / "GLOSSARY.md"
    if _write_text_if_missing(
        glossary_path,
        "# Glossary\n\n"
        "Domain terms, abbreviations, and conventions used across problems.\n",
    ):
        created.append("research/global/GLOSSARY.md")

    # Per-problem workspace
    (research_root / "problems").mkdir(parents=True, exist_ok=True)
    problem_dir.mkdir(parents=True, exist_ok=True)

    meta_path = problem_dir / "meta.yaml"
    if _write_yaml_if_missing(
        meta_path,
        {
            "schema_version": 1,
            "problem_id": problem_id,
            "created_at": utc_now_iso_z(now),
            "updated_at": utc_now_iso_z(now),
        },
    ):
        created.append(f"research/problems/{problem_id:04d}/meta.yaml")

    readme_path = problem_dir / "README.md"
    if _write_text_if_missing(
        readme_path,
        f"# Problem {problem_id:04d}\n\n"
        "Repo-local research workspace (v3).\n\n"
        "- `SCRATCHPAD.md`: append-only notes\n"
        "- `SYNTHESIS.md`: curated current state (always fed into RAG/loop)\n",
    ):
        created.append(f"research/problems/{problem_id:04d}/README.md")

    scratchpad_path = problem_dir / "SCRATCHPAD.md"
    if _write_text_if_missing(
        scratchpad_path,
        "# Scratchpad\n\n"
        "Append-only notes. Use:\n\n"
        f'- `erdos research note {problem_id} "..."`\n',
    ):
        created.append(f"research/problems/{problem_id:04d}/SCRATCHPAD.md")

    synthesis_path = problem_dir / "SYNTHESIS.md"
    if _write_text_if_missing(
        synthesis_path,
        f"# Synthesis: Problem {problem_id:04d}\n\n"
        "Run `erdos research synthesize` to regenerate this file.\n",
    ):
        created.append(f"research/problems/{problem_id:04d}/SYNTHESIS.md")

    for folder in ("leads", "attempts", "hypotheses", "tasks"):
        dir_path = problem_dir / folder
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(f"research/problems/{problem_id:04d}/{folder}")

    return WorkspaceInitResult(
        problem_id=problem_id,
        research_root=research_root,
        problem_dir=problem_dir,
        created_paths=tuple(created),
    )
