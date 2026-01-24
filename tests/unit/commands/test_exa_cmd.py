"""Unit tests for `erdos research exa` command (SPEC-029)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import responses

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


# Sample Exa API response for mocking
SAMPLE_EXA_RESPONSE: dict[str, Any] = {
    "autopromptString": "Research on sum-free sets approaches",
    "results": [
        {
            "url": "https://arxiv.org/abs/math/0404188",
            "title": "The primes contain arbitrarily long arithmetic progressions",
            "author": "Ben Green, Terence Tao",
            "publishedDate": "2008-04-01",
            "text": "This paper proves that the prime numbers contain...",
            "score": 0.95,
            "id": "result-1",
        },
        {
            "url": "https://doi.org/10.1007/s00222-016-0678-7",
            "title": "Sum-free sets in abelian groups",
            "author": "Sean Eberhard",
            "publishedDate": "2016-07-15",
            "text": "We study sum-free sets in abelian groups...",
            "score": 0.88,
            "id": "result-2",
        },
    ],
    "summary": "Several approaches have been tried for sum-free sets...",
}


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    """Set up test environment with sample data and API key."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
        "EXA_API_KEY": "test-api-key",
    }


class TestExaSearchCommand:
    """Tests for `erdos research exa search` command."""

    @responses.activate
    def test_search_success(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Successful search returns structured output."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)
        # Disable caching by using a unique cache path
        cache_path = tmp_path / "exa_cache"
        env["ERDOS_EXA_CACHE_PATH"] = str(cache_path)

        result = runner.invoke(
            app,
            [
                "--json",
                "research",
                "exa",
                "search",
                "6",
                "sum-free sets approaches",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}\n{result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos research exa"
        assert payload["data"]["problem_id"] == 6
        assert payload["data"]["query"] == "sum-free sets approaches"
        assert len(payload["data"]["sources"]) == 2
        assert payload["data"]["sources"][0]["title"] == (
            "The primes contain arbitrarily long arithmetic progressions"
        )
        assert payload["data"]["sources"][0]["arxiv_id"] == "math/0404188"
        assert payload["data"]["answer"] == (
            "Several approaches have been tried for sum-free sets..."
        )

    @responses.activate
    def test_search_with_max_results(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """max_results parameter is passed to API."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)
        # Use unique cache path to avoid cache pollution
        cache_path = tmp_path / "exa_cache"
        env["ERDOS_EXA_CACHE_PATH"] = str(cache_path)

        result = runner.invoke(
            app,
            [
                "--json",
                "research",
                "exa",
                "search",
                "6",
                "test query max results",
                "--max-results",
                "10",
            ],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["data"]["max_results"] == 10

        # Verify request body
        request = responses.calls[0].request
        assert request.body is not None
        body = json.loads(request.body)
        assert body["numResults"] == 10

    def test_search_missing_api_key(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Returns error when EXA_API_KEY not set."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
        env = {
            "ERDOS_DATA_PATH": str(data_dir),
            "ERDOS_REPO_ROOT": str(tmp_path),
            # Explicitly unset EXA_API_KEY (may be set via .env)
            "EXA_API_KEY": "",
        }

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", "test query"],
            env=env,
        )

        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "ConfigError"
        assert "EXA_API_KEY" in payload["error"]["message"]

    def test_search_problem_not_found(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Returns error when problem doesn't exist."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "99999", "test query"],
            env=env,
        )

        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert "99999" in payload["error"]["message"]

    @responses.activate
    def test_search_api_error(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Handles API errors gracefully."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json={"error": "Internal server error"},
            status=500,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", "test query"],
            env=env,
        )

        # May fail or succeed depending on retry behavior, but should not crash
        payload = json.loads(result.stdout)
        assert "command" in payload


class TestExaSaveLeads:
    """Tests for --save-leads functionality."""

    @responses.activate
    def test_save_leads_creates_records(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """--save-leads creates lead records from sources."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        # Initialize workspace first
        init_result = runner.invoke(
            app,
            ["--json", "research", "init", "6"],
            env=env,
        )
        assert init_result.exit_code == 0

        # Run search with --save-leads
        result = runner.invoke(
            app,
            [
                "--json",
                "research",
                "exa",
                "search",
                "6",
                "sum-free sets",
                "--save-leads",
            ],
            env=env,
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)

        assert payload["data"]["saved_leads"] is True
        assert len(payload["data"]["created_lead_ids"]) == 2

        # Verify leads were created
        leads_result = runner.invoke(
            app,
            ["--json", "research", "lead", "list", "6"],
            env=env,
        )
        assert leads_result.exit_code == 0
        leads_payload = json.loads(leads_result.stdout)

        # Should have 2 leads from the Exa results
        assert len(leads_payload["data"]["records"]) >= 2

        # Verify lead content
        lead_titles = [r["title"] for r in leads_payload["data"]["records"]]
        assert (
            "The primes contain arbitrarily long arithmetic progressions" in lead_titles
        )
        assert "Sum-free sets in abelian groups" in lead_titles

    @responses.activate
    def test_save_leads_false_by_default(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Leads are not saved by default."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", "test query"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["data"]["saved_leads"] is False
        assert payload["data"]["created_lead_ids"] == []


class TestExaJsonSchema:
    """Tests for JSON output schema conformance (SPEC-029)."""

    @responses.activate
    def test_json_output_schema(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """JSON output matches documented schema."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", "test query"],
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

        # Required data fields
        data = payload["data"]
        assert "problem_id" in data
        assert "query" in data
        assert "max_results" in data
        assert "sources" in data
        assert "answer" in data
        assert "saved_leads" in data
        assert "created_lead_ids" in data
        assert "cached" in data
        assert "cache_path" in data

        # Source fields
        if data["sources"]:
            source = data["sources"][0]
            assert "title" in source
            assert "url" in source
            assert "authors" in source
            assert "year" in source
            # arxiv_id and doi may be null
            assert "arxiv_id" in source
            assert "doi" in source
            assert "relevance" in source


class TestExaHumanOutput:
    """Tests for human-readable output."""

    @responses.activate
    def test_human_output_format(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Human-readable output is well-formatted."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["research", "exa", "search", "6", "sum-free sets"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout

        # Check for key elements in human output
        assert "Query:" in output
        assert "Sources" in output
        assert "Green" in output or "primes" in output.lower()


class TestExaCaching:
    """Tests for response caching behavior."""

    @responses.activate
    def test_cached_flag_in_output(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """cached flag indicates whether result came from cache."""
        # Use unique cache path to isolate from other tests
        cache_path = tmp_path / "exa_cache"
        unique_query = f"unique query {tmp_path.name}"

        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)
        env["ERDOS_EXA_CACHE_PATH"] = str(cache_path)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", unique_query],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        # First call is not cached
        assert payload["data"]["cached"] is False

        # Second call should be cached
        result2 = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", unique_query],
            env=env,
        )

        assert result2.exit_code == 0
        payload2 = json.loads(result2.stdout)
        # Now it should be cached
        assert payload2["data"]["cached"] is True

    @responses.activate
    def test_cache_path_in_output(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """cache_path is included in output."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "research", "exa", "search", "6", "test query"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert "cache_path" in payload["data"]
        assert payload["data"]["cache_path"].endswith(".json")
