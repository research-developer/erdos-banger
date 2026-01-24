"""Tests for submodule sync CLI command (SPEC-035/3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from erdos.commands.sync.submodule_cmd import sync_submodule
from erdos.core.sync.models import SubmoduleSyncStatus
from erdos.core.sync.submodule import (
    SubmoduleFetchError,
    SubmoduleNotInitializedError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_problems_yaml() -> str:
    """Sample problems.yaml content matching upstream format."""
    return """
- number: '1'
  prize: $500
  status:
    state: proved
    last_update: '2025-01-01'
  oeis:
    - N/A
  formalized:
    state: 'yes'
    last_update: '2025-02-01'
  tags:
    - number theory
- number: '2'
  prize: 'no'
  status:
    state: open
  oeis:
    - A000001
  formalized:
    state: 'no'
  tags:
    - combinatorics
"""


@pytest.fixture
def mock_submodule_dir(tmp_path: Path, sample_problems_yaml: str) -> Path:
    """Create a mock submodule directory structure."""
    submodule_dir = tmp_path / "erdosproblems"
    data_dir = submodule_dir / "data"
    data_dir.mkdir(parents=True)

    # Write problems.yaml
    (data_dir / "problems.yaml").write_text(sample_problems_yaml, encoding="utf-8")

    # Create a fake .git file to simulate submodule
    (submodule_dir / ".git").write_text("gitdir: ../.git/modules/erdosproblems")

    return submodule_dir


# =============================================================================
# sync_submodule tests
# =============================================================================


class TestSyncSubmodule:
    """Tests for sync_submodule() core function."""

    def test_successful_update(self, mock_submodule_dir: Path, tmp_path: Path) -> None:
        """Successful update returns CLIOutput with correct data."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123def456"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="abc123def456",
                    previous_commit_hash="old789",
                    stale=False,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH",
                    tmp_path / "cache",
                ):
                    result = sync_submodule(
                        check_only=False, submodule_path=mock_submodule_dir
                    )

        assert result.success is True
        assert result.data is not None
        assert result.data["checked"] is False
        assert result.data["updated"] is True
        assert result.data["current_commit"] == "abc123def456"
        assert result.data["previous_commit"] == "old789"

    def test_check_only_not_stale(
        self, mock_submodule_dir: Path, tmp_path: Path
    ) -> None:
        """Check-only mode returns correct staleness status."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="abc123",
                    previous_commit_hash="abc123",
                    stale=False,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH",
                    tmp_path / "cache",
                ):
                    result = sync_submodule(
                        check_only=True, submodule_path=mock_submodule_dir
                    )

        assert result.success is True
        assert result.data is not None
        assert result.data["checked"] is True
        assert result.data["stale"] is False

    def test_check_only_is_stale(
        self, mock_submodule_dir: Path, tmp_path: Path
    ) -> None:
        """Check-only mode returns stale=True when behind remote."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="abc123",
                    previous_commit_hash="abc123",
                    stale=True,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH",
                    tmp_path / "cache",
                ):
                    result = sync_submodule(
                        check_only=True, submodule_path=mock_submodule_dir
                    )

        assert result.success is True
        assert result.data is not None
        assert result.data["checked"] is True
        assert result.data["stale"] is True

    def test_not_initialized_error(self, tmp_path: Path) -> None:
        """Returns error when submodule not initialized."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.side_effect = SubmoduleNotInitializedError(
                "Submodule not initialized"
            )
            result = sync_submodule(
                check_only=False, submodule_path=tmp_path / "nonexistent"
            )

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "NotInitializedError"
        assert "not initialized" in result.error["message"].lower()

    def test_fetch_error(self, mock_submodule_dir: Path) -> None:
        """Returns error when fetch fails (network error)."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.side_effect = SubmoduleFetchError("Network error")
                result = sync_submodule(
                    check_only=False, submodule_path=mock_submodule_dir
                )

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "FetchError"
        assert "network" in result.error["message"].lower()

    def test_counts_problems(self, mock_submodule_dir: Path, tmp_path: Path) -> None:
        """Counts problems from submodule data."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="abc123",
                    previous_commit_hash="abc123",
                    stale=False,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH",
                    tmp_path / "cache",
                ):
                    result = sync_submodule(
                        check_only=False, submodule_path=mock_submodule_dir
                    )

        assert result.success is True
        assert result.data is not None
        # Should have counted 2 problems from fixture
        assert result.data["problems_count"] == 2

    def test_saves_sync_status_cache(
        self, mock_submodule_dir: Path, tmp_path: Path
    ) -> None:
        """Saves sync status to cache file."""
        cache_path = tmp_path / "cache"

        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="abc123",
                    previous_commit_hash="abc123",
                    stale=False,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH", cache_path
                ):
                    result = sync_submodule(
                        check_only=False, submodule_path=mock_submodule_dir
                    )

        assert result.success is True
        status_file = cache_path / "submodule_status.json"
        assert status_file.exists()


# =============================================================================
# JSON output contract tests
# =============================================================================


class TestJsonOutputContract:
    """Tests verifying JSON output matches SPEC-035 contract."""

    def test_success_output_shape(
        self, mock_submodule_dir: Path, tmp_path: Path
    ) -> None:
        """Successful output has correct shape per spec."""
        with patch(
            "erdos.commands.sync.submodule_cmd.get_submodule_commit"
        ) as mock_commit:
            mock_commit.return_value = "abc123def456"
            with patch(
                "erdos.commands.sync.submodule_cmd.update_submodule"
            ) as mock_update:
                mock_update.return_value = SubmoduleSyncStatus(
                    commit_hash="new456",
                    previous_commit_hash="old123",
                    stale=False,
                )
                with patch(
                    "erdos.commands.sync.submodule_cmd.SYNC_CACHE_PATH",
                    tmp_path / "cache",
                ):
                    result = sync_submodule(
                        check_only=False, submodule_path=mock_submodule_dir
                    )

        # Verify JSON structure matches spec:
        # { "checked": bool, "updated": bool, "previous_commit": str | null,
        #   "current_commit": str | null, "stale": bool | null }
        data = result.data
        assert data is not None

        # Required fields per spec
        assert "checked" in data
        assert "updated" in data
        assert "previous_commit" in data
        assert "current_commit" in data
        assert "stale" in data

        # Types
        assert isinstance(data["checked"], bool)
        assert isinstance(data["updated"], bool)
        assert data["previous_commit"] is None or isinstance(
            data["previous_commit"], str
        )
        assert data["current_commit"] is None or isinstance(data["current_commit"], str)
        assert data["stale"] is None or isinstance(data["stale"], bool)
