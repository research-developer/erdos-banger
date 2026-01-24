"""Tests for erdos sync proof command (SPEC-035)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from erdos.commands.sync.proof_cmd import sync_proof_links
from erdos.core.exit_codes import ExitCode


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "forum"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def html_thread_with_github() -> str:
    """Forum thread with a GitHub proof link."""
    return load_fixture("thread_347_with_github_link.html")


@pytest.fixture
def html_thread_no_links() -> str:
    """Forum thread with no proof links."""
    return load_fixture("thread_no_links.html")


@pytest.fixture
def html_thread_multiple_links() -> str:
    """Forum thread with multiple links."""
    return load_fixture("thread_with_multiple_links.html")


# =============================================================================
# sync_proof_links core logic tests
# =============================================================================


class TestSyncProofLinks:
    """Tests for the sync_proof_links core logic."""

    def test_extracts_github_link(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Extract GitHub link from forum HTML."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(347, html_content=html_thread_with_github)

        assert result.success is True
        assert result.data is not None
        assert result.data["problem_id"] == 347
        assert result.data["links_count"] == 1
        assert (
            result.data["links"][0]["url"]
            == "https://github.com/mathprover123/erdos-347-proof"
        )

    def test_extracts_multiple_links(
        self, html_thread_multiple_links: str, tmp_path: Path
    ) -> None:
        """Extract multiple links from forum HTML."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(100, html_content=html_thread_multiple_links)

        assert result.success is True
        assert result.data["links_count"] == 3

    def test_handles_no_links(self, html_thread_no_links: str, tmp_path: Path) -> None:
        """Handle forum with no proof links gracefully."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(50, html_content=html_thread_no_links)

        assert result.success is True
        assert result.data["links_count"] == 0
        assert result.data["links"] == []

    def test_dry_run_does_not_write(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Dry run mode does not write files."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(
                347, html_content=html_thread_with_github, dry_run=True
            )

        assert result.success is True
        # Cache directory should not exist
        assert not (tmp_path / "proofs" / "347").exists()

    def test_writes_links_json(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Sync writes links.json to cache directory."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(347, html_content=html_thread_with_github)

        assert result.success is True
        links_path = tmp_path / "proofs" / "347" / "links.json"
        assert links_path.exists()

        with links_path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["problem_id"] == 347
        assert len(data["links"]) == 1

    def test_json_output_contract(
        self, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """Verify JSON output matches spec contract."""
        with patch(
            "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
        ):
            result = sync_proof_links(347, html_content=html_thread_with_github)

        assert result.success is True
        data = result.data

        # Check required fields per SPEC-035
        assert "problem_id" in data
        assert "links" in data
        assert isinstance(data["links"], list)
        assert "provenance_path" in data
        assert "verification_status" in data

        # Each link must have url field
        for link in data["links"]:
            assert "url" in link


# =============================================================================
# CLI integration tests
# =============================================================================


class TestProofCLI:
    """CLI integration tests for erdos sync proof."""

    def test_help_message(self, runner: CliRunner) -> None:
        """Help message displays correctly."""
        result = runner.invoke(app, ["sync", "proof", "--help"])
        assert result.exit_code == 0
        assert "Extract proof repository links" in result.output

    def test_json_output(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """JSON output mode works correctly."""
        with (
            patch("erdos.commands.sync.proof_cmd.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            # Mock to return parsed data from fixture
            from erdos.core.sync.forum import parse_forum_html

            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["--json", "sync", "proof", "347"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["problem_id"] == 347
        assert data["data"]["links_count"] == 1

    def test_dry_run_option(
        self, runner: CliRunner, html_thread_with_github: str, tmp_path: Path
    ) -> None:
        """--dry-run option prevents file writes."""
        with (
            patch("erdos.commands.sync.proof_cmd.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            from erdos.core.sync.forum import parse_forum_html

            mock_fetch.return_value = parse_forum_html(html_thread_with_github, 347)

            result = runner.invoke(app, ["sync", "proof", "347", "--dry-run"])

        assert result.exit_code == 0
        # Should not create cache directory
        assert not (tmp_path / "proofs" / "347").exists()

    def test_network_error_handling(self, runner: CliRunner, tmp_path: Path) -> None:
        """Network errors are handled gracefully."""
        from erdos.core.sync.forum import ForumFetchError

        with (
            patch("erdos.commands.sync.proof_cmd.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            mock_fetch.side_effect = ForumFetchError("Connection refused")

            result = runner.invoke(app, ["--json", "sync", "proof", "347"])

        assert result.exit_code == ExitCode.NETWORK_ERROR.value
        data = json.loads(result.output)
        assert data["success"] is False
        assert "Connection refused" in data["error"]["message"]

    def test_not_found_error(self, runner: CliRunner, tmp_path: Path) -> None:
        """404 errors return NOT_FOUND exit code."""
        from erdos.core.sync.forum import ForumFetchError

        with (
            patch("erdos.commands.sync.proof_cmd.fetch_and_parse_forum") as mock_fetch,
            patch(
                "erdos.commands.sync.proof_cmd.DEFAULT_CACHE_PATH", tmp_path / "proofs"
            ),
        ):
            mock_fetch.side_effect = ForumFetchError(
                "Forum thread not found", status_code=404
            )

            result = runner.invoke(app, ["--json", "sync", "proof", "9999"])

        assert result.exit_code == ExitCode.NOT_FOUND.value
