"""Unit tests for `erdos search --msc` MSC search mode (SPEC-031/3)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import responses

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


# Sample zbMATH API responses for mocking
SAMPLE_MSC_SEARCH_RESPONSE: dict[str, Any] = {
    "result": [
        {
            "id": 5578697,
            "identifier": "1191.11025",
            "title": {
                "title": "The primes contain arbitrarily long arithmetic progressions"
            },
            "contributors": {
                "authors": [
                    {"name": "Green, Ben"},
                    {"name": "Tao, Terence"},
                ]
            },
            "year": "2008",
            "links": [
                {"type": "doi", "identifier": "10.4007/annals.2008.167.481"},
                {"type": "arxiv", "identifier": "math.NT/0404188"},
            ],
            "source": {
                "series": [
                    {"title": "Annals of Mathematics", "short_title": "Ann. Math."}
                ]
            },
            "msc": [
                {
                    "code": "11B05",
                    "text": "Density, gaps, topology",
                    "scheme": "msc2020",
                },
                {
                    "code": "11N13",
                    "text": "Primes in progressions",
                    "scheme": "msc2020",
                },
            ],
            "keywords": ["arithmetic progressions", "primes"],
            "editorial_contributions": [
                {
                    "contribution_type": "review",
                    "text": "A landmark paper in number theory...",
                }
            ],
            "zbmath_url": "https://zbmath.org/?q=an:1191.11025",
        },
        {
            "id": 3663470,
            "identifier": "0426.28014",
            "title": {
                "title": "An ergodic Szemerédi theorem for commuting transformations"
            },
            "contributors": {
                "authors": [
                    {"name": "Furstenberg, H."},
                    {"name": "Katznelson, Y."},
                ]
            },
            "year": "1978",
            "links": [{"type": "doi", "identifier": "10.1007/BF02790016"}],
            "source": {"series": []},
            "msc": [
                {
                    "code": "11B05",
                    "text": "Density, gaps, topology",
                    "scheme": "msc2020",
                },
                {
                    "code": "11B25",
                    "text": "Arithmetic progressions",
                    "scheme": "msc2020",
                },
            ],
            "keywords": ["ergodic Szemerédi theorem"],
            "editorial_contributions": [],
            "zbmath_url": "https://zbmath.org/?q=an:0426.28014",
        },
    ]
}

SAMPLE_EMPTY_RESPONSE: dict[str, Any] = {"result": []}


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


class TestSearchMscBasic:
    """Tests for `erdos search --msc` basic functionality."""

    @responses.activate
    def test_msc_search_returns_zbmath_entries(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--msc flag triggers zbMATH MSC search."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}\n{result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos search"
        assert payload["data"]["mode"] == "msc"
        assert payload["data"]["msc"] == "11B05"
        assert "entries" in payload["data"]
        assert len(payload["data"]["entries"]) == 2

    @responses.activate
    def test_msc_search_with_limit(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--limit is passed to zbMATH API."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05", "--limit", "5"],
            env=env,
        )

        assert result.exit_code == 0
        # Verify limit was passed in request
        request = responses.calls[0].request
        assert request.url is not None
        assert "results_per_page=5" in request.url

    @responses.activate
    def test_msc_search_with_year_range(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--year-min and --year-max are passed to zbMATH API."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "search",
                "--msc",
                "11B05",
                "--year-min",
                "2000",
                "--year-max",
                "2020",
            ],
            env=env,
        )

        assert result.exit_code == 0
        # Verify year range was passed in search query
        request = responses.calls[0].request
        assert request.url is not None
        # py: is URL-encoded as py%3A
        assert "py%3A2000-2020" in request.url or "py:2000-2020" in request.url

    @responses.activate
    def test_msc_search_empty_results(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Empty results return success with empty entries list."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_EMPTY_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "99Z99"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["data"]["entries"] == []


class TestSearchMscMutualExclusion:
    """Tests that --msc mode is mutually exclusive with normal search."""

    @responses.activate
    def test_msc_ignores_query_argument(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """When --msc is provided, the query argument is ignored."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        # Provide both a query and --msc; --msc should take precedence
        result = runner.invoke(
            app,
            ["--json", "search", "some query", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["data"]["mode"] == "msc"
        # Should have queried zbMATH by MSC, not local search
        assert "entries" in payload["data"]

    @responses.activate
    def test_msc_incompatible_with_semantic(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--msc and --semantic are mutually exclusive."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05", "--semantic"],
            env=env,
        )

        # Should fail with usage error
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "UsageError"
        assert "--msc" in payload["error"]["message"]

    @responses.activate
    def test_msc_incompatible_with_hybrid(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--msc and --hybrid are mutually exclusive."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05", "--hybrid"],
            env=env,
        )

        # Should fail with usage error
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "UsageError"

    @responses.activate
    def test_msc_incompatible_with_build_index(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--msc and --build-index are mutually exclusive."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05", "--build-index"],
            env=env,
        )

        # Should fail with usage error
        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "UsageError"


class TestSearchMscJsonSchema:
    """Tests for JSON output schema conformance."""

    @responses.activate
    def test_json_schema_conforms_to_spec(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """JSON output matches SPEC-031 schema."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        # Required top-level fields
        assert "schema_version" in payload
        assert "command" in payload
        assert "success" in payload
        assert "data" in payload
        assert "error" in payload
        assert "timestamp" in payload
        assert "duration_ms" in payload

        # Required data fields for MSC search
        data = payload["data"]
        assert data["mode"] == "msc"
        assert "msc" in data
        assert "entries" in data

        # Entry fields per SPEC-031
        if data["entries"]:
            entry = data["entries"][0]
            assert "zbl_id" in entry
            assert "title" in entry
            assert "authors" in entry
            assert "year" in entry
            assert "doi" in entry
            assert "msc" in entry
            assert "keywords" in entry

            # MSC code fields
            if entry["msc"]:
                msc = entry["msc"][0]
                assert "code" in msc
                assert "text" in msc
                assert "primary" in msc


class TestSearchMscHumanOutput:
    """Tests for human-readable output."""

    @responses.activate
    def test_human_output_shows_results(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Human output shows search results."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["search", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout

        # Should show MSC code and results
        assert "11B05" in output
        # Should show titles or authors
        assert "primes" in output.lower() or "Green" in output

    @responses.activate
    def test_human_output_empty_results(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Human output handles empty results."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_EMPTY_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["search", "--msc", "99Z99"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout
        # Should indicate no results
        assert "0" in output or "No" in output or "no" in output


class TestSearchMscCaching:
    """Tests for caching behavior."""

    @responses.activate
    def test_caching_reduces_api_calls(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Second call uses cache."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_MSC_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        # First call
        result1 = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05"],
            env=env,
        )
        assert result1.exit_code == 0
        assert len(responses.calls) == 1

        # Second call should use cache
        result2 = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05"],
            env=env,
        )
        assert result2.exit_code == 0
        # Still only 1 call - cache was used
        assert len(responses.calls) == 1


class TestSearchMscErrorHandling:
    """Tests for error handling."""

    @responses.activate
    def test_handles_api_error(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Handles zbMATH API errors gracefully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"error": "Internal server error"},
            status=500,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "search", "--msc", "11B05"],
            env=env,
        )

        # Should return error, not crash
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "ZbMathError"
