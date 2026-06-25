"""Repository root + data-home discovery helpers.

Data historically lived under the project root (data/, logs/, index/, ...).
The `erdos` CLI can now run from anywhere (installed as a global tool / Claude
plugin), so data resolves to a fixed *data home*:

    1. $ERDOS_HOME, if set (and non-empty)
    2. a discovered project root (when running inside a checkout)
    3. ~/.erdos (default)

`repo_path()` anchors all data paths on this home.
"""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DATA_HOME = Path.home() / ".erdos"


def _looks_like_repo_root(path: Path) -> bool:
    """Return True if `path` appears to be the erdos-banger project root."""
    return (path / "pyproject.toml").is_file() and (path / "src" / "erdos").is_dir()


def discover_repo_root(start: Path | None = None) -> Path | None:
    """Discover the repository root by walking ancestors from `start`."""
    resolved = (start or Path.cwd()).resolve()
    for candidate in (resolved, *resolved.parents):
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def data_home() -> Path:
    """Resolve the centralized data home (see module docstring)."""
    explicit = os.environ.get("ERDOS_HOME")
    if explicit and explicit.strip():
        return Path(explicit).expanduser().resolve()
    discovered = discover_repo_root()
    if discovered is not None:
        return discovered
    return DEFAULT_DATA_HOME.resolve()


def resolve_repo_root(repo_root: Path | None) -> Path:
    """Resolve a usable base directory.

    Explicit `repo_root` wins; otherwise the data home is used (which prefers a
    discovered checkout, falling back to ~/.erdos).
    """
    if repo_root is not None:
        return repo_root.resolve()
    return data_home()


def repo_path(*parts: str) -> Path:
    """Absolute path under the data home. Use instead of hardcoded `Path("data/...")`."""
    return data_home().joinpath(*parts)
