"""Tests for erdos sync website command (SPEC-035)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from erdos.commands.sync.website_cmd import sync_website_problem
from erdos.core.models import ProblemRecord


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "website"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def html_problem_6_proved() -> str:
    """HTML fixture for problem #6 (PROVED status)."""
    return load_fixture("problem_6_proved.html")


@pytest.fixture
def html_problem_minimal() -> str:
    """HTML fixture for a minimal problem page."""
    return load_fixture("problem_minimal.html")


@pytest.fixture
def html_problem_no_content() -> str:
    """HTML fixture without content (should fail merge)."""
    return load_fixture("problem_no_content.html")


# =============================================================================
# Core logic tests (using fixtures, no network)
# =============================================================================


class TestSyncWebsiteProblem:
    """Tests for sync_website_problem core logic."""

    def test_sync_with_fixture_returns_success(
        self, html_problem_6_proved: str
    ) -> None:
        """Sync with HTML fixture should succeed."""
        result = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=True,
        )

        assert result.success is True
        assert result.data["problem_id"] == 6
        assert result.data["cached"] is True  # Used fixture
        assert "title" in result.data

    def test_sync_with_minimal_fixture(self, html_problem_minimal: str) -> None:
        """Sync with minimal HTML should work."""
        result = sync_website_problem(
            problem_id=99,
            html_content=html_problem_minimal,
            dry_run=True,
        )

        assert result.success is True
        assert result.data["problem_id"] == 99
        assert result.data["title"] is not None

    def test_sync_without_content_fails(self, html_problem_no_content: str) -> None:
        """Sync with missing content should fail (missing required fields)."""
        result = sync_website_problem(
            problem_id=404,
            html_content=html_problem_no_content,
            dry_run=True,
        )

        # Should fail because merge requires title and statement
        assert result.success is False
        assert result.error is not None
        assert "missing required fields" in result.error.get("message", "").lower()

    def test_dry_run_does_not_write(
        self,
        html_problem_6_proved: str,
        tmp_path: Path,
    ) -> None:
        """dry_run=True should not write to disk."""
        data_path = tmp_path / "problems.yaml"
        cache_path = tmp_path / "cache"

        result = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=True,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )

        assert result.success is True
        assert not data_path.exists()

    def test_sync_writes_to_disk_when_not_dry_run(
        self,
        html_problem_6_proved: str,
        tmp_path: Path,
    ) -> None:
        """sync without dry_run should write to disk."""
        data_path = tmp_path / "problems_enriched.yaml"
        cache_path = tmp_path / "cache"

        result = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=False,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )

        assert result.success is True
        assert result.data["updated"] is True
        assert data_path.exists()

        # Verify the written data is valid YAML
        with data_path.open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 6

    def test_sync_merges_with_existing(
        self,
        html_problem_6_proved: str,
        tmp_path: Path,
    ) -> None:
        """Sync should merge with existing problem data."""
        data_path = tmp_path / "problems_enriched.yaml"
        cache_path = tmp_path / "cache"

        # Create existing data with notes
        existing_data = [
            {
                "id": 6,
                "title": "Old Title",
                "statement": "Old statement",
                "status": "open",
                "notes": "Important notes to preserve",
            }
        ]
        with data_path.open("w") as f:
            yaml.dump(existing_data, f)

        result = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=False,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )

        assert result.success is True

        # Verify notes were preserved
        with data_path.open() as f:
            data = yaml.safe_load(f)
        assert data[0]["notes"] == "Important notes to preserve"
        # But title/statement should be updated from website
        assert data[0]["title"] != "Old Title"

    def test_updated_false_when_no_changes(
        self,
        html_problem_6_proved: str,
        tmp_path: Path,
    ) -> None:
        """updated should be False when syncing unchanged data."""
        data_path = tmp_path / "problems_enriched.yaml"
        cache_path = tmp_path / "cache"

        # First sync
        result1 = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=False,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )
        assert result1.data["updated"] is True

        # Second sync with same content
        result2 = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=False,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )
        assert result2.data["updated"] is False


class TestSyncWebsiteProblemOutputContract:
    """Tests for the JSON output contract per SPEC-035."""

    def test_success_output_has_required_fields(
        self, html_problem_6_proved: str
    ) -> None:
        """Success output should match spec contract."""
        result = sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=True,
        )

        assert result.success is True
        data = result.data

        # Verify required fields per SPEC-035 JSON output contract
        assert "problem_id" in data
        assert isinstance(data["problem_id"], int)
        assert "updated" in data
        assert isinstance(data["updated"], bool)
        assert "latex_saved" in data
        assert isinstance(data["latex_saved"], bool)
        assert "cached" in data
        assert isinstance(data["cached"], bool)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    def test_error_output_has_required_fields(
        self, html_problem_no_content: str
    ) -> None:
        """Error output should have error type and message."""
        result = sync_website_problem(
            problem_id=404,
            html_content=html_problem_no_content,
            dry_run=True,
        )

        assert result.success is False
        assert result.error is not None
        assert "type" in result.error
        assert "message" in result.error


class TestProblemLoaderCompatibility:
    """Tests to ensure output is ProblemLoader-compatible."""

    def test_output_can_be_loaded_by_problem_record(
        self,
        html_problem_6_proved: str,
        tmp_path: Path,
    ) -> None:
        """Written YAML should be parseable as ProblemRecord."""
        data_path = tmp_path / "problems_enriched.yaml"
        cache_path = tmp_path / "cache"

        sync_website_problem(
            problem_id=6,
            html_content=html_problem_6_proved,
            dry_run=False,
            data_path=data_path,
            sync_cache_dir=cache_path,
        )

        with data_path.open() as f:
            data = yaml.safe_load(f)

        # Should be parseable as ProblemRecord (strict=False to handle enum serialization)
        record = ProblemRecord.model_validate(data[0], strict=False)
        assert record.id == 6
        assert record.title is not None
        assert record.statement is not None
