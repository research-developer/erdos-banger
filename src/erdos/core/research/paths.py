"""Research path helpers (filesystem SSOT).

All paths are derived from:
- repo_root (if provided, from AppConfig.repo_root), else
- Path.cwd() (assumed to be repo root)
"""

from __future__ import annotations

from pathlib import Path


WORKSPACE_VERSION = 1


def get_workspace_version() -> int:
    return WORKSPACE_VERSION


def get_repo_root(repo_root: Path | None) -> Path:
    root = repo_root if repo_root is not None else Path.cwd()
    return root.resolve()


def get_research_root(repo_root: Path | None) -> Path:
    return get_repo_root(repo_root) / "research"


def get_problem_dir(repo_root: Path | None, problem_id: int) -> Path:
    if problem_id < 1:
        raise ValueError(f"problem_id must be >= 1, got {problem_id}")
    return get_research_root(repo_root) / "problems" / f"{problem_id:04d}"
