"""Integration tests for Semantic Scholar API (SPEC-030).

These tests require network access.
They are skipped by default; run with `pytest -m requires_network`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    """Set up test environment with sample data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
        "ERDOS_S2_CACHE_PATH": str(tmp_path / "s2_cache"),
    }


@pytest.mark.requires_network
class TestS2NetworkIntegration:
    """Network integration tests for Semantic Scholar API."""

    def test_s2_citations_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """End-to-end citations fetch using real S2 API.

        Uses the famous Green-Tao paper on arithmetic progressions in primes.
        This paper has many citations so should always return results.
        """
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "10.4007/annals.2008.167.481",
                "--limit",
                "3",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 citations"
        assert payload["data"]["identifier"] == "10.4007/annals.2008.167.481"
        # Green-Tao paper metadata
        assert "paper" in payload["data"]
        assert payload["data"]["paper"]["title"] is not None
        # Should have some citations
        assert "citations" in payload["data"]
        assert payload["data"]["total_citations"] > 0

    def test_s2_citations_arxiv_id_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Test citations with arXiv ID."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "math/0404188",  # Green-Tao
                "--limit",
                "2",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert "paper" in payload["data"]
        assert payload["data"]["paper"]["arxiv_id"] == "math/0404188"

    def test_s2_cited_by_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Test cited-by command with real API."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "cited-by",
                "10.4007/annals.2008.167.481",
                "--limit",
                "5",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 cited-by"
        assert "citing_papers" in payload["data"]
        assert payload["data"]["total_citations"] > 0

    def test_s2_references_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Test references command with real API."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "references",
                "10.4007/annals.2008.167.481",
                "--limit",
                "5",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 references"
        assert "references" in payload["data"]
        # Green-Tao paper cites many papers
        assert payload["data"]["returned"] > 0

    def test_s2_caching_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Verify caching works with real API.

        Second request should use cache, not make additional API calls.
        """
        env = _setup_env(tmp_path, sample_problems_yaml)

        # First request
        result1 = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "10.4007/annals.2008.167.481",
                "--limit",
                "2",
            ],
            env=env,
        )

        assert result1.exit_code == 0
        payload1 = json.loads(result1.stdout)
        assert payload1["success"] is True

        # Second request (should use cache)
        result2 = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "10.4007/annals.2008.167.481",
                "--limit",
                "2",
            ],
            env=env,
        )

        assert result2.exit_code == 0
        payload2 = json.loads(result2.stdout)
        assert payload2["success"] is True

        # Results should be identical (from cache)
        assert payload1["data"]["paper"]["s2_id"] == payload2["data"]["paper"]["s2_id"]

    def test_s2_not_found_paper(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Test behavior with non-existent paper."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "10.9999/nonexistent.paper.doi",
            ],
            env=env,
        )

        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "NotFound"
