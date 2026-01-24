"""Unit tests for `erdos refs s2` commands (SPEC-030)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import responses

from erdos.cli import app
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


# Sample S2 API responses for mocking
SAMPLE_PAPER_RESPONSE: dict[str, Any] = {
    "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
    "title": "The primes contain arbitrarily long arithmetic progressions",
    "authors": [
        {"authorId": "1", "name": "Ben Green"},
        {"authorId": "2", "name": "Terence Tao"},
    ],
    "year": 2008,
    "externalIds": {
        "ArXiv": "math/0404188",
        "DOI": "10.4007/annals.2008.167.481",
    },
    "citationCount": 1234,
}

SAMPLE_CITATIONS_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "citingPaper": {
                "paperId": "abc123",
                "title": "New bounds on sum-free sets",
                "year": 2015,
            },
            "intents": ["methodology"],
            "contexts": [
                "Using the density increment strategy of Green-Tao [12], we show..."
            ],
        },
        {
            "citingPaper": {
                "paperId": "def456",
                "title": "Arithmetic progressions in random subsets",
                "year": 2019,
            },
            "intents": ["background"],
            "contexts": ["Since the breakthrough result of [GT08], there has been..."],
        },
        {
            "citingPaper": {
                "paperId": "ghi789",
                "title": "A contrasting result",
                "year": 2021,
            },
            "intents": ["result"],
            "contexts": [
                "While Green-Tao established positive density, we show that..."
            ],
        },
    ]
}

SAMPLE_REFERENCES_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "citedPaper": {
                "paperId": "ref123",
                "title": "Szemeredi's theorem",
                "year": 1975,
            },
            "intents": ["background", "methodology"],
            "contexts": ["Building on Szemeredi's seminal work..."],
        },
        {
            "citedPaper": {
                "paperId": "ref456",
                "title": "An earlier result",
                "year": 1965,
            },
            "intents": ["background"],
            "contexts": [],
        },
    ]
}


def _setup_env(tmp_path: Path, sample_problems_yaml: Path) -> dict[str, str]:
    """Set up test environment with sample data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    cache_path = tmp_path / "s2_cache"
    return {
        "ERDOS_DATA_PATH": str(data_dir),
        "ERDOS_REPO_ROOT": str(tmp_path),
        # Use unique cache path to avoid cache pollution
        "ERDOS_S2_CACHE_PATH": str(cache_path),
    }


class TestRefsS2Citations:
    """Tests for `erdos refs s2 citations` command."""

    @responses.activate
    def test_citations_with_doi(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Fetches citation contexts by DOI."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            [
                "--json",
                "refs",
                "s2",
                "citations",
                "10.4007/annals.2008.167.481",
            ],
            env=env,
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}\n{result.stdout}"
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 citations"
        assert payload["data"]["identifier"] == "10.4007/annals.2008.167.481"
        assert payload["data"]["paper"]["title"] == (
            "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(payload["data"]["citations"]) == 3
        assert payload["data"]["citations"][0]["intents"] == ["methodology"]
        assert (
            "density increment strategy"
            in payload["data"]["citations"][0]["contexts"][0]
        )

    @responses.activate
    def test_citations_with_arxiv_id(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Fetches citation contexts by arXiv ID."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/ARXIV:math/0404188",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "math/0404188"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert len(payload["data"]["citations"]) == 3

    @responses.activate
    def test_citations_with_limit(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Respects --limit option."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/test",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.1234/test", "--limit", "5"],
            env=env,
        )

        assert result.exit_code == 0
        # Verify limit was passed to API
        request = responses.calls[1].request
        assert request.url is not None
        assert "limit=5" in request.url

    @responses.activate
    def test_citations_paper_not_found(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Returns error when paper not found."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/nonexistent",
            json={"error": "Not found"},
            status=404,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.1234/nonexistent"],
            env=env,
        )

        assert result.exit_code != 0
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["type"] == "NotFound"


class TestRefsS2CitedBy:
    """Tests for `erdos refs s2 cited-by` command."""

    @responses.activate
    def test_cited_by_success(self, tmp_path: Path, sample_problems_yaml: Path) -> None:
        """Lists papers citing the given paper."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "cited-by", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 cited-by"
        assert len(payload["data"]["citing_papers"]) == 3
        assert (
            payload["data"]["citing_papers"][0]["title"]
            == "New bounds on sum-free sets"
        )

    @responses.activate
    def test_cited_by_with_limit(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Respects --limit option."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/test",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "cited-by", "10.1234/test", "--limit", "20"],
            env=env,
        )

        assert result.exit_code == 0
        request = responses.calls[1].request
        assert request.url is not None
        assert "limit=20" in request.url


class TestRefsS2References:
    """Tests for `erdos refs s2 references` command."""

    @responses.activate
    def test_references_success(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Lists papers referenced by the given paper."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/references",
            json=SAMPLE_REFERENCES_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "references", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)

        assert payload["success"] is True
        assert payload["command"] == "erdos refs s2 references"
        assert len(payload["data"]["references"]) == 2
        assert payload["data"]["references"][0]["title"] == "Szemeredi's theorem"
        assert payload["data"]["references"][0]["intents"] == [
            "background",
            "methodology",
        ]

    @responses.activate
    def test_references_with_limit(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Respects --limit option."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/test",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/references",
            json=SAMPLE_REFERENCES_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "references", "10.1234/test", "--limit", "15"],
            env=env,
        )

        assert result.exit_code == 0
        request = responses.calls[1].request
        assert request.url is not None
        assert "limit=15" in request.url


class TestRefsS2JsonSchema:
    """Tests for JSON output schema conformance (SPEC-030)."""

    @responses.activate
    def test_citations_json_schema(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Citations JSON output matches documented schema."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.4007/annals.2008.167.481"],
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

        # Required data fields per SPEC-030
        data = payload["data"]
        assert "identifier" in data
        assert "paper" in data
        assert "citations" in data
        assert "total_citations" in data
        assert "returned" in data

        # Paper fields
        paper = data["paper"]
        assert "title" in paper
        assert "authors" in paper
        assert "year" in paper
        assert "s2_id" in paper
        assert "doi" in paper
        assert "arxiv_id" in paper

        # Citation fields
        if data["citations"]:
            citation = data["citations"][0]
            assert "citing_paper" in citation
            assert "intents" in citation
            assert "contexts" in citation
            assert "title" in citation["citing_paper"]
            assert "year" in citation["citing_paper"]
            assert "s2_id" in citation["citing_paper"]


class TestRefsS2HumanOutput:
    """Tests for human-readable output."""

    @responses.activate
    def test_citations_human_output(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Human-readable output is well-formatted."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["refs", "s2", "citations", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        output = result.stdout

        # Check for key elements in human output
        assert "Paper:" in output or "primes" in output.lower()
        assert "Green" in output or "Tao" in output
        assert "Citing" in output or "citations" in output.lower()


class TestRefsProblemCommand:
    """Tests for `erdos refs problem <problem_id>` command."""

    def test_refs_problem_command(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """`erdos refs problem <id>` shows problem references."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "problem", "6"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["command"] == "erdos refs"
        assert payload["data"]["problem_id"] == 6

    def test_refs_backward_compat_numeric_arg(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """`erdos refs <id>` works for backward compatibility (SPEC-030)."""
        env = _setup_env(tmp_path, sample_problems_yaml)

        result = runner.invoke(
            app,
            ["--json", "refs", "6"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["command"] == "erdos refs"
        assert payload["data"]["problem_id"] == 6
        assert "references" in payload["data"]


class TestRefsS2Caching:
    """Tests for response caching behavior."""

    @responses.activate
    def test_caching_reduces_api_calls(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Second call uses cache, no additional API calls."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)

        # First call makes API requests
        result1 = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.4007/annals.2008.167.481"],
            env=env,
        )
        assert result1.exit_code == 0
        assert len(responses.calls) == 2

        # Second call should use cache (no new API calls)
        result2 = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.4007/annals.2008.167.481"],
            env=env,
        )
        assert result2.exit_code == 0
        # Still only 2 calls - cache was used
        assert len(responses.calls) == 2


class TestRefsS2Graceful:
    """Tests for graceful degradation without API key."""

    @responses.activate
    def test_works_without_api_key(
        self, tmp_path: Path, sample_problems_yaml: Path
    ) -> None:
        """Works without SEMANTIC_SCHOLAR_API_KEY (unauthenticated)."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        env = _setup_env(tmp_path, sample_problems_yaml)
        # Ensure no API key is set
        env.pop("SEMANTIC_SCHOLAR_API_KEY", None)

        result = runner.invoke(
            app,
            ["--json", "refs", "s2", "citations", "10.4007/annals.2008.167.481"],
            env=env,
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True

        # Verify no x-api-key in headers
        request = responses.calls[0].request
        assert "x-api-key" not in request.headers
