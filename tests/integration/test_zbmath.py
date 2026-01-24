"""Integration tests for zbMATH API (SPEC-031).

These tests hit the real zbMATH Open API and are skipped by default.
Run with: pytest -m requires_network tests/integration/test_zbmath.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from erdos.cli import app
from erdos.core.clients.zbmath import ZbMathClient, ZbMathConfig
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    """Set up test environment with sample data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    cache_path = tmp_path / "zbmath_cache"
    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
        "ERDOS_ZBMATH_CACHE_PATH": str(cache_path),
    }


@pytest.mark.requires_network
class TestZbMathClientIntegration:
    """Integration tests for ZbMathClient with real API."""

    def test_get_by_doi_real(self, tmp_path: Path) -> None:
        """Fetch entry by DOI from real API."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        # Green-Tao paper
        entry = client.get_by_doi("10.4007/annals.2008.167.481", use_cache=False)

        assert entry is not None
        assert "arithmetic progressions" in entry.title.lower()
        assert len(entry.authors) >= 2
        assert entry.year == 2008
        # Should have MSC codes
        assert len(entry.msc) > 0

    def test_get_by_zbl_id_real(self, tmp_path: Path) -> None:
        """Fetch entry by zbMATH ID from real API."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        # Green-Tao paper zbl ID
        entry = client.get_by_zbl_id("1191.11025", use_cache=False)

        assert entry is not None
        assert "primes" in entry.title.lower() or "arithmetic" in entry.title.lower()

    def test_search_by_msc_real(self, tmp_path: Path) -> None:
        """Search by MSC code from real API."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        # 11B05 = Density, gaps, topology
        entries = client.search_by_msc("11B05", limit=5, use_cache=False)

        assert len(entries) > 0
        # All entries should have at least one MSC code
        for entry in entries:
            assert len(entry.msc) > 0

    def test_search_by_title_real(self, tmp_path: Path) -> None:
        """Search by title from real API."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        entries = client.search_by_title("Szemerédi theorem", limit=3, use_cache=False)

        assert len(entries) > 0
        # Results should be relevant
        for entry in entries:
            assert "szemerédi" in entry.title.lower() or len(entry.msc) > 0


@pytest.mark.requires_network
class TestRefsZbMathCLIIntegration:
    """Integration tests for `erdos refs zbmath` CLI with real API."""

    def test_cli_lookup_by_doi(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """CLI lookup by DOI from real API."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["data"]["entry"]["title"] is not None
        assert len(payload["data"]["entry"]["msc"]) > 0

    def test_cli_msc_search(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """CLI MSC search from real API."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--msc", "05D10", "--limit", "3"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert len(payload["data"]["entries"]) > 0

    def test_cli_lookup_not_found(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """CLI handles not found gracefully."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.9999/nonexistent.paper.12345"],
            env=env,
        )

        # Should return error, not crash
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "NotFound"
