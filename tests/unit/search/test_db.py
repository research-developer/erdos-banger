"""Unit tests for DatabaseManager (DEBT-117 fixes).

Tests for the database connection management and error handling.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from erdos.core.search.db import DatabaseManager


class TestDatabaseManagerConnect:
    """Tests for DatabaseManager.connect() context manager."""

    def test_connect_creates_connection(self, tmp_path: Path) -> None:
        """connect() creates a valid database connection."""
        db = DatabaseManager(tmp_path / "test.sqlite")
        with db.connect() as conn:
            assert isinstance(conn, sqlite3.Connection)
            # Can execute queries
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    def test_connect_commits_on_success(self, tmp_path: Path) -> None:
        """connect() commits transaction on successful exit."""
        db = DatabaseManager(tmp_path / "test.sqlite")
        with db.connect() as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")

        # Verify data persisted
        with db.connect() as conn:
            cursor = conn.execute("SELECT id FROM test")
            assert cursor.fetchone()[0] == 1

    def test_connect_rollback_on_exception(self, tmp_path: Path) -> None:
        """connect() rolls back transaction on exception."""
        db = DatabaseManager(tmp_path / "test.sqlite")
        with db.connect() as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")

        with pytest.raises(ValueError), db.connect() as conn:
            conn.execute("INSERT INTO test VALUES (1)")
            raise ValueError("Test exception")

        # Verify insert was rolled back
        with db.connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            assert cursor.fetchone()[0] == 0

    def test_connect_handles_connection_error(self, tmp_path: Path) -> None:
        """connect() handles sqlite3.connect() failure without secondary exception.

        This is the DEBT-117 fix: if sqlite3.connect() raises, the finally block
        should not raise UnboundLocalError trying to close an undefined conn.
        """
        db = DatabaseManager(tmp_path / "test.sqlite")

        # Mock sqlite3.connect to raise an error
        with (
            patch(
                "erdos.core.search.db.sqlite3.connect",
                side_effect=sqlite3.OperationalError("disk full"),
            ),
            pytest.raises(sqlite3.OperationalError, match="disk full"),
            db.connect(),
        ):
            pass  # Should never reach here

    def test_connect_handles_permission_error(self, tmp_path: Path) -> None:
        """connect() handles permission errors gracefully."""
        db = DatabaseManager(tmp_path / "test.sqlite")

        with (
            patch(
                "erdos.core.search.db.sqlite3.connect",
                side_effect=sqlite3.OperationalError("unable to open database file"),
            ),
            pytest.raises(sqlite3.OperationalError, match="unable to open"),
            db.connect(),
        ):
            pass

    def test_connect_closes_connection_on_normal_exit(self, tmp_path: Path) -> None:
        """connect() closes connection after normal exit."""
        db = DatabaseManager(tmp_path / "test.sqlite")

        with db.connect() as conn:
            # Connection is open
            conn.execute("SELECT 1")

        # After context exit, connection should be closed
        # Trying to use it should raise
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_connect_closes_connection_on_exception(self, tmp_path: Path) -> None:
        """connect() closes connection even when exception occurs."""
        db = DatabaseManager(tmp_path / "test.sqlite")
        captured_conn: sqlite3.Connection | None = None

        with pytest.raises(ValueError), db.connect() as conn:
            captured_conn = conn
            raise ValueError("Test error")

        # Connection should be closed after exception
        assert captured_conn is not None
        with pytest.raises(sqlite3.ProgrammingError):
            captured_conn.execute("SELECT 1")
