"""Research path helpers (filesystem SSOT).

All paths are derived from:
- repo_root (if provided, from AppConfig.repo_root), else
- Path.cwd() (assumed to be repo root)
"""

from __future__ import annotations

from pathlib import Path


WORKSPACE_VERSION = 1


def get_workspace_version() -> int:
    """Return the research workspace schema version."""
    return WORKSPACE_VERSION


def get_repo_root(repo_root: Path | None) -> Path:
    """Resolve the repository root path.

    Args:
        repo_root: Optional repository root. If None, uses the current working
            directory.

    Returns:
        Absolute, resolved repository root path.
    """
    root = repo_root if repo_root is not None else Path.cwd()
    return root.resolve()


def get_research_root(repo_root: Path | None) -> Path:
    """Return the `research/` directory path under the repo root.

    Args:
        repo_root: Optional repository root. If None, uses the current working
            directory.

    Returns:
        Absolute path to the research workspace root directory.
    """
    return get_repo_root(repo_root) / "research"


def get_problem_dir(repo_root: Path | None, problem_id: int) -> Path:
    """Return the problem workspace directory path.

    Args:
        repo_root: Optional repository root. If None, uses the current working
            directory.
        problem_id: Erdős problem ID (must be >= 1).

    Returns:
        Absolute path to `research/problems/{problem_id:04d}`.

    Raises:
        ValueError: If `problem_id` is < 1.
    """
    if problem_id < 1:
        raise ValueError(f"problem_id must be >= 1, got {problem_id}")
    return get_research_root(repo_root) / "problems" / f"{problem_id:04d}"
