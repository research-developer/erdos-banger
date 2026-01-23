"""Problem research workspace status (Spec 023)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from erdos.core.research.paths import get_problem_dir


if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ProblemWorkspaceStatus:
    problem_id: int
    problem_dir: Path
    files: dict[str, bool]
    counts: dict[str, int]


def _count_yaml_files(dir_path: Path) -> int:
    if not dir_path.exists() or not dir_path.is_dir():
        return 0
    return len([p for p in dir_path.iterdir() if p.is_file() and p.suffix == ".yaml"])


def get_problem_status(
    problem_id: int, *, repo_root: Path | None
) -> ProblemWorkspaceStatus:
    problem_dir = get_problem_dir(repo_root, problem_id)
    files = {
        "meta": (problem_dir / "meta.yaml").exists(),
        "scratchpad": (problem_dir / "SCRATCHPAD.md").exists(),
        "synthesis": (problem_dir / "SYNTHESIS.md").exists(),
    }
    counts = {
        "leads": _count_yaml_files(problem_dir / "leads"),
        "attempts": _count_yaml_files(problem_dir / "attempts"),
        "hypotheses": _count_yaml_files(problem_dir / "hypotheses"),
        "tasks": _count_yaml_files(problem_dir / "tasks"),
    }
    return ProblemWorkspaceStatus(
        problem_id=problem_id,
        problem_dir=problem_dir,
        files=files,
        counts=counts,
    )
