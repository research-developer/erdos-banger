"""Minimal passing integration test placeholder."""

import sqlite3
from pathlib import Path


def test_integration_placeholder(
    temp_project_dir: Path, in_memory_db: sqlite3.Connection
) -> None:
    assert (temp_project_dir / "data").exists()
    cursor = in_memory_db.execute("SELECT 1")
    assert cursor.fetchone() == (1,)
