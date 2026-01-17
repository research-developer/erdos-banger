"""Verify our testing infrastructure is correctly configured."""

from pathlib import Path

import pytest


def test_pytest_markers_are_registered(pytestconfig: pytest.Config) -> None:
    """All custom markers should be registered to avoid warnings."""
    markers = pytestconfig.getini("markers")
    expected = {"slow", "e2e", "requires_lean", "requires_network"}
    registered = {m.split(":", 1)[0].strip() for m in markers}
    assert expected.issubset(registered)


def test_fixtures_directory_exists(fixtures_dir: Path) -> None:
    """Fixtures directory should exist and contain expected files."""
    assert fixtures_dir.exists()
    assert fixtures_dir.is_dir()


def test_in_memory_db_fixture_provides_connection(in_memory_db) -> None:
    """in_memory_db fixture should provide a working SQLite connection."""
    cursor = in_memory_db.execute("SELECT 1")
    assert cursor.fetchone() == (1,)
