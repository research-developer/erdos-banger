"""Minimal .env loader for CLI ergonomics.

This intentionally mirrors the behavior of `scripts/lib/load-env.sh`:
- simple KEY=value parsing
- ignores empty lines and comments
- supports single/double quoted values
- strips inline comments for unquoted values (everything after '#')
- does not support multiline values or shell expansion

Unlike many dotenv loaders, this module defaults to **not** overriding existing
environment variables (including empty-string values).
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

if TYPE_CHECKING:
    from pathlib import Path


def load_dotenv_file(path: Path, *, override: bool = False) -> dict[str, str]:
    """Load variables from a .env file into `os.environ`.

    Args:
        path: Path to the .env file. Missing files are treated as a no-op.
        override: If True, override existing environment variables.

    Returns:
        Dict of variables that were set (i.e., applied to os.environ).
    """
    if not path.is_file():
        return {}

    loaded: dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        key_part, sep, value_part = line.partition("=")
        if not sep:
            continue

        key = key_part.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()

        if not key or not _KEY_RE.match(key):
            continue

        value = value_part.strip()
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]
        else:
            value = value.split("#", 1)[0].strip()

        if not override and key in os.environ:
            continue

        os.environ[key] = value
        loaded[key] = value

    return loaded
