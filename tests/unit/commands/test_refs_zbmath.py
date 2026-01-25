"""Unit tests for `erdos refs zbmath` commands (SPEC-031)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import responses

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


# Sample zbMATH API responses for mocking (based on real API structure)
SAMPLE_ENTRY_RESPONSE: dict[str, Any] = {
    "result": {
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
            "series": [{"title": "Annals of Mathematics", "short_title": "Ann. Math."}]
        },
        "msc": [
            {"code": "11B05", "text": "Density, gaps, topology", "scheme": "msc2020"},
            {"code": "11N13", "text": "Primes in progressions", "scheme": "msc2020"},
            {"code": "05D10", "text": "Ramsey theory", "scheme": "msc2020"},
        ],
        "keywords": ["arithmetic progressions", "primes", "density", "ergodic methods"],
        "editorial_contributions": [
            {
                "contribution_type": "review",
                "text": "The authors prove that the prime numbers contain arbitrarily long arithmetic progressions. This resolves a long-standing conjecture dating back to Erdős. The proof uses techniques from additive combinatorics and ergodic theory.",
            }
        ],
        "zbmath_url": "https://zbmath.org/?q=an:1191.11025",
    }
}

SAMPLE_SEARCH_RESPONSE: dict[str, Any] = {
    "result": [
        SAMPLE_ENTRY_RESPONSE["result"],
        {
            "id": 1234567,
            "identifier": "1234.11001",
            "title": {"title": "Another paper on arithmetic progressions"},
            "contributors": {"authors": [{"name": "Smith, John"}]},
            "year": "2015",
            "links": [],
            "source": {"series": []},
            "msc": [
                {
                    "code": "11B25",
                    "text": "Arithmetic progressions",
                    "scheme": "msc2020",
                }
            ],
            "keywords": ["arithmetic progressions"],
            "editorial_contributions": [],
            "zbmath_url": "https://zbmath.org/?q=an:1234.11001",
        },
    ]
}

SAMPLE_EMPTY_SEARCH_RESPONSE: dict[str, Any] = {"result": []}


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    """Set up test environment with sample data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    cache_path = tmp_path / "zbmath_cache"
    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
        # Use unique cache path to avoid cache pollution
        "ERDOS_ZBMATH_CACHE_PATH": str(cache_path),
    }


class TestRefsZbMathLookup:
    """Tests for `erdos refs zbmath` lookup command."""

    @responses.activate
    def test_lookup_by_doi(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Fetches entry by DOI."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}\n{result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs zbmath"
        assert (
            payload["data"]["entry"]["title"]
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert payload["data"]["entry"]["authors"] == ["Green, Ben", "Tao, Terence"]
        assert len(payload["data"]["entry"]["msc"]) == 3
        assert payload["data"]["entry"]["msc"][0]["code"] == "11B05"
        assert payload["data"]["entry"]["msc"][0]["primary"] is True

    @responses.activate
    def test_lookup_by_zbl_id(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Fetches entry by zbMATH ID."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--zbl", "1191.11025"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["data"]["entry"]["zbl_id"] == "1191.11025"

    @responses.activate
    def test_lookup_by_title(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Fetches entry by title search."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--title", "primes arithmetic progressions"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True

    @responses.activate
    def test_lookup_not_found(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Returns error when entry not found."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_EMPTY_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.1234/nonexistent"],
            env=env,
        )

        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "NotFoundError"


class TestRefsZbMathMscSearch:
    """Tests for `erdos refs zbmath --msc` search command."""

    @responses.activate
    def test_msc_search_success(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Searches by MSC code."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs zbmath"
        assert "entries" in payload["data"]
        assert len(payload["data"]["entries"]) == 2

    @responses.activate
    def test_msc_search_with_year_range(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Respects --year-min and --year-max options."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "zbmath",
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
        # Verify year range was passed in search query (URL-encoded)
        request = responses.calls[0].request
        assert request.url is not None
        # py: is URL-encoded as py%3A
        assert "py%3A2000-2020" in request.url or "py:2000-2020" in request.url

    @responses.activate
    def test_msc_search_with_limit(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Respects --limit option."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--msc", "11B05", "--limit", "5"],
            env=env,
        )

        assert result.exit_code == 0
        request = responses.calls[0].request
        assert request.url is not None
        assert "results_per_page=5" in request.url

    @responses.activate
    def test_msc_search_empty_results(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Returns empty list when no results."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_EMPTY_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "--msc", "99Z99"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["data"]["entries"] == []


class TestRefsZbMathJsonSchema:
    """Tests for JSON output schema conformance (SPEC-031)."""

    @responses.activate
    def test_lookup_json_schema(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Lookup JSON output matches documented schema."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
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

        # Required data fields per SPEC-031
        data = payload["data"]
        assert "identifier" in data
        assert "entry" in data

        # Entry fields
        entry = data["entry"]
        assert "zbl_id" in entry
        assert "title" in entry
        assert "authors" in entry
        assert "year" in entry
        assert "doi" in entry
        assert "msc" in entry
        assert "keywords" in entry
        assert "review_excerpt" in entry

        # MSC code fields
        if entry["msc"]:
            msc = entry["msc"][0]
            assert "code" in msc
            assert "text" in msc
            assert "primary" in msc


class TestRefsZbMathHumanOutput:
    """Tests for human-readable output."""

    @responses.activate
    def test_lookup_human_output(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Human-readable output is well-formatted."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout

        # Check for key elements in human output
        assert "zbMATH" in output or "Zbl" in output
        assert "Green" in output or "Tao" in output
        assert "MSC" in output or "11B05" in output

    @responses.activate
    def test_msc_search_human_output(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """MSC search human output is well-formatted."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["refs", "zbmath", "--msc", "11B05"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout

        # Check for result formatting
        assert "primes" in output.lower() or "arithmetic" in output.lower()


class TestRefsZbMathCaching:
    """Tests for response caching behavior."""

    @responses.activate
    def test_caching_reduces_api_calls(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Second call uses cache, no additional API calls."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        # First call makes API request
        result1 = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )
        assert result1.exit_code == 0
        assert len(responses.calls) == 1

        # Second call should use cache (no new API calls)
        result2 = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )
        assert result2.exit_code == 0
        # Still only 1 call - cache was used
        assert len(responses.calls) == 1


class TestRefsZbMathGraceful:
    """Tests for graceful degradation."""

    @responses.activate
    def test_works_without_mailto(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Works without ERDOS_MAILTO (open API)."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_ENTRY_RESPONSE["result"]]},
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)
        # Ensure no mailto is set
        env.pop("ERDOS_MAILTO", None)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True

    @responses.activate
    def test_handles_server_error(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Handles server errors gracefully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"error": "Internal server error"},
            status=500,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "zbmath", "10.4007/annals.2008.167.481"],
            env=env,
        )

        # Should return error, not crash
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "ZbMathError"
