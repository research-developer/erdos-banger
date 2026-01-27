"""Repository root discovery helpers.

Many commands assume paths like `logs/`, `data/`, and `research/` live under the
project root. Users often run `erdos` from subdirectories (e.g., `formal/lean/`),
so we need a lightweight way to resolve the repo root consistently without
requiring `ERDOS_REPO_ROOT` to be set.
"""

from __future__ import annotations

from pathlib import Path


def _looks_like_repo_root(path: Path) -> bool:
    """Return True if `path` appears to be the erdos-banger project root."""
    return (path / "pyproject.toml").is_file() and (path / "src" / "erdos").is_dir()


def discover_repo_root(start: Path | None = None) -> Path | None:
    """Discover the repository root by walking ancestors from `start`.

    Returns the first ancestor directory that looks like the project root, or
    None if no such directory is found.
    """
    resolved = (start or Path.cwd()).resolve()
    for candidate in (resolved, *resolved.parents):
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def resolve_repo_root(repo_root: Path | None) -> Path:
    """Resolve a usable repository root.

    If `repo_root` is provided, it is resolved and returned. Otherwise, attempts
    discovery from the current working directory, falling back to the current
    working directory if discovery fails.
    """
    if repo_root is not None:
        return repo_root.resolve()
    return discover_repo_root() or Path.cwd().resolve()
