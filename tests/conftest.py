"""Shared fixtures for all tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator

from erdos.core.models import ProblemRecord, ProblemStatus


@pytest.fixture
def sample_problem() -> ProblemRecord:
    """A minimal valid ProblemRecord for testing."""
    return ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Prove that P implies Q.",
        status=ProblemStatus.OPEN,
        prize=100,
        tags=["number theory"],
        references=[],
    )


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_problems_yaml(fixtures_dir: Path) -> Path:
    """Path to sample problems.yaml for testing."""
    return fixtures_dir / "sample_problems.yaml"


@pytest.fixture
def in_memory_db() -> Iterator[sqlite3.Connection]:
    """SQLite in-memory database for search index tests."""
    conn = sqlite3.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()
