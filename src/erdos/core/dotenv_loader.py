"""Minimal .env loader for CLI ergonomics.

This intentionally mirrors the behavior of `scripts/lib/load-env.sh`:
- simple KEY=value parsing
- ignores empty lines and comments
- supports single/double quoted values
- strips inline comments for unquoted values (everything after '#')
- does not support multiline values or shell expansion
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

if TYPE_CHECKING:
    from pathlib import Path


def parse_dotenv_content(content: str) -> dict[str, str]:
    """Parse .env file content to a dictionary."""
    parsed: dict[str, str] = {}
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

        parsed[key] = value

    return parsed


def load_dotenv_file(path: Path) -> dict[str, str]:
    """Load and parse variables from a .env file.

    Args:
        path: Path to the .env file. Missing/unreadable files are treated as a no-op.

    Returns:
        Dict of parsed variables from the file.
    """
    if not path.is_file():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    return parse_dotenv_content(content)
