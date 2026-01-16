"""Fixtures for integration tests - real components, isolated environment."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary project directory with required structure."""
    (tmp_path / "data" / "erdosproblems").mkdir(parents=True)
    (tmp_path / "formal" / "lean" / "Erdos").mkdir(parents=True)
    (tmp_path / "index").mkdir()
    (tmp_path / "logs").mkdir()

    yield tmp_path


# Note: in_memory_db fixture is defined in tests/conftest.py (shared)
# to support root-level meta-tests per Spec 002 Section 11.
