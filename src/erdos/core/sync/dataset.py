"""Local enriched dataset I/O helpers (SPEC-035).

These helpers load and save the local enriched problems dataset
(`problems_enriched.yaml`) as `ProblemRecord` models.

They are intentionally small and deterministic so sync commands can share them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from erdos.core.models import ProblemRecord


if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


def load_enriched_problems(path: Path) -> dict[int, ProblemRecord]:
    """Load the enriched problems dataset from disk.

    Returns an empty dict if the file is missing or unreadable.
    """
    if not path.exists():
        return {}

    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load enriched dataset %s: %s", path, e)
        return {}

    if not isinstance(data, list):
        logger.warning("Invalid enriched dataset format (expected list): %s", path)
        return {}

    problems: dict[int, ProblemRecord] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_id: Any = item.get("id")
        if raw_id is None:
            continue
        try:
            record = ProblemRecord.model_validate(item, strict=False)
        except (ValidationError, ValueError):
            continue
        problems[record.id] = record

    return problems


def save_enriched_problems(path: Path, problems: dict[int, ProblemRecord]) -> None:
    """Save the enriched problems dataset to disk (atomic write)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    sorted_problems = sorted(problems.values(), key=lambda p: p.id)
    data = [p.model_dump(mode="json") for p in sorted_problems]

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
    tmp_path.replace(path)
