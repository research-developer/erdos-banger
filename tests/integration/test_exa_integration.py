"""Integration tests for Exa Research API (SPEC-029).

These tests require network access and a valid EXA_API_KEY.
They are skipped by default; run with `pytest -m requires_network`.
"""

from __future__ import annotations

import json
import os
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
        "ERDOS_EXA_CACHE_PATH": str(tmp_path / "exa_cache"),
    }


@pytest.mark.requires_network
class TestExaNetworkIntegration:
    """Network integration tests for Exa API."""

    def test_exa_search_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """End-to-end search using real Exa API.

        This test requires EXA_API_KEY to be set in the environment.
        """
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            pytest.skip("EXA_API_KEY not set")

        env = _setup_env(tmp_path, sample_problems_yaml)
        env["EXA_API_KEY"] = api_key

        result = runner.invoke(
            app,
            [
                "--json",
                "research",
                "exa",
                "search",
                "6",
                "arithmetic progressions in primes",
                "--max-results",
                "3",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Failed: {result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos research exa"
        assert payload["data"]["problem_id"] == 6
        assert "sources" in payload["data"]
        # Real API should return at least some results
        assert len(payload["data"]["sources"]) > 0

    def test_exa_search_caching_real_api(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Verify caching works with real API.

        First request should hit API, second should be cached.
        """
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            pytest.skip("EXA_API_KEY not set")

        env = _setup_env(tmp_path, sample_problems_yaml)
        env["EXA_API_KEY"] = api_key

        # Unique query to avoid cache pollution
        query = "unique cache test query for erdos integration testing 2026"

        # First request
        result1 = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", query, "--max-results", "2"],
            env=env,
        )

        assert result1.exit_code == 0
        payload1 = json.loads(result1.stdout)
        assert payload1["data"]["cached"] is False

        # Second request (should be cached)
        result2 = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", query, "--max-results", "2"],
            env=env,
        )

        assert result2.exit_code == 0
        payload2 = json.loads(result2.stdout)
        assert payload2["data"]["cached"] is True
