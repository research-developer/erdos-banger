"""Canonical YAML IO for research records."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, Any

import yaml


if TYPE_CHECKING:
    from pathlib import Path


def dump_yaml(data: Any) -> str:
    """Dump data to canonical YAML (deterministic)."""
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return text if text.endswith("\n") else text + "\n"


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML: {e}") from e


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_handle, tmp_path_str = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    tmp = path.__class__(tmp_path_str)
    try:
        with os.fdopen(tmp_handle, "w", encoding="utf-8") as f:
            f.write(content)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
