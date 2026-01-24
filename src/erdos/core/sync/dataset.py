"""Local enriched dataset I/O helpers (SPEC-035).

These helpers load and save the local enriched problems dataset
(`problems_enriched.yaml`) as `ProblemRecord` models.

They are intentionally small and deterministic so sync commands can share them.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from erdos.core.models import ProblemRecord


if TYPE_CHECKING:
    from erdos.core.config import AppConfig

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
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            logger.debug(
                "Skipping non-dict dataset entry at index %d (type=%s)",
                idx,
                type(item).__name__,
            )
            continue
        raw_id: Any = item.get("id")
        if raw_id is None:
            logger.debug("Skipping dataset entry missing id at index %d", idx)
            continue
        try:
            record = ProblemRecord.model_validate(item, strict=False)
        except (ValidationError, ValueError):
            logger.debug(
                "Skipping invalid dataset entry id=%r at index %d",
                raw_id,
                idx,
            )
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


def resolve_enriched_dataset_path(config: AppConfig) -> Path:
    """Resolve the enriched dataset path from configuration.

    This mirrors the behavior used elsewhere in the system:
    - If ERDOS_DATA_PATH points to a directory, look for problems_enriched.yaml
      or problems.yaml in that directory.
    - If ERDOS_DATA_PATH points to a file (existing or not), use it directly.
    - Otherwise, default to <repo_root>/data/problems_enriched.yaml when
      ERDOS_REPO_ROOT is set, or ./data/problems_enriched.yaml when not.
    """
    base_dir = config.repo_root or Path.cwd()

    if config.data_path is None:
        return base_dir / "data" / "problems_enriched.yaml"

    configured = config.data_path
    if not configured.is_absolute():
        configured = base_dir / configured

    # Directory: choose an existing dataset file, or default to problems_enriched.yaml
    if configured.exists() and configured.is_dir():
        for filename in ("problems_enriched.yaml", "problems.yaml"):
            candidate = configured / filename
            if candidate.exists():
                return candidate
        return configured / "problems_enriched.yaml"

    # File path (existing or not)
    return configured


def resolve_sync_cache_dir(dataset_path: Path) -> Path:
    """Resolve the sync cache directory for a dataset file path."""
    return dataset_path.parent / "sync_cache"
