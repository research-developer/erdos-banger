"""Shared fixtures for all tests."""

from __future__ import annotations

import os


# IMPORTANT: Unset PY_COLORS BEFORE importing Rich/Typer.
# pytest --color=yes sets PY_COLORS=1, which causes Typer's rich_utils.py to set
# FORCE_TERMINAL=True at import time. This makes Rich emit ANSI codes and truncate
# help panels, breaking tests that assert on --help output.
# See: https://github.com/pallets/click/issues/1997
if "PY_COLORS" in os.environ:
    del os.environ["PY_COLORS"]

import re
import sqlite3
from collections.abc import Callable
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


@pytest.fixture
def arxiv_atom_fixture(fixtures_dir: Path) -> str:
    """Load arXiv atom XML fixture for testing."""
    return (fixtures_dir / "arxiv_responses" / "arxiv_2203.00001.xml").read_text()


@pytest.fixture
def arxiv_math_0404188_fixture(fixtures_dir: Path) -> str:
    """Load arXiv atom XML fixture for math/0404188 (problem 6)."""
    return (fixtures_dir / "arxiv_responses" / "arxiv_math_0404188.xml").read_text()


@pytest.fixture
def crossref_annals_fixture(fixtures_dir: Path) -> str:
    """Load Crossref JSON fixture for 10.4007/annals.2008.167.481 (problem 6)."""
    return (
        fixtures_dir / "crossref_responses" / "doi_10.4007_annals.2008.167.481.json"
    ).read_text()


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Strip ANSI escape sequences from captured CLI output.

    Typer+Rich may emit styling codes depending on environment. Tests asserting on
    help text should normalize output before matching.
    """

    def _strip(text: str) -> str:
        return _ANSI_ESCAPE_RE.sub("", text)

    return _strip
