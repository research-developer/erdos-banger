"""Unit tests for Semantic Scholar API client."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import requests
import responses

from erdos.core.clients.semantic_scholar import (
    CitationContext,
    S2Config,
    S2Paper,
    S2Reference,
    SemanticScholarClient,
)


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

SAMPLE_PAPER_RESPONSE: dict[str, Any] = json.loads(
    (FIXTURES_DIR / "semantic_scholar_responses" / "paper_green_tao.json").read_text()
)
SAMPLE_CITATIONS_RESPONSE: dict[str, Any] = json.loads(
    (
        FIXTURES_DIR / "semantic_scholar_responses" / "citations_green_tao.json"
    ).read_text()
)
SAMPLE_REFERENCES_RESPONSE: dict[str, Any] = json.loads(
    (
        FIXTURES_DIR / "semantic_scholar_responses" / "references_green_tao.json"
    ).read_text()
)


class TestS2Config:
    """Tests for S2Config."""

    def test_default_config(self) -> None:
        """Config has sensible defaults."""
        config = S2Config()
        assert config.api_key is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_ttl_days == 7
        assert config.cache_path == Path("literature/cache/s2")

    def test_from_env_with_api_key(self) -> None:
        """Config loads SEMANTIC_SCHOLAR_API_KEY from environment."""
        with patch.dict(
            os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "test-key-123"}, clear=False
        ):
            config = S2Config.from_env()
            assert config.api_key == "test-key-123"

    def test_from_env_with_cache_ttl(self) -> None:
        """Config loads ERDOS_S2_CACHE_TTL from environment."""
        env = {"SEMANTIC_SCHOLAR_API_KEY": "key", "ERDOS_S2_CACHE_TTL": "14"}
        with patch.dict(os.environ, env, clear=False):
            config = S2Config.from_env()
            assert config.cache_ttl_days == 14

    def test_from_env_uses_app_config(self) -> None:
        """Config uses centralized AppConfig for SEMANTIC_SCHOLAR_API_KEY."""
        with patch.dict(
            os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "app-config-key"}, clear=False
        ):
            config = S2Config.from_env()
            assert config.api_key == "app-config-key"


class TestS2Paper:
    """Tests for S2Paper dataclass."""

    def test_parse_from_api_response(self) -> None:
        """Parses paper from API response."""
        paper = S2Paper.from_api_response(SAMPLE_PAPER_RESPONSE)

        assert (
            paper.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert paper.s2_id == "649def34f8be52c8b66281af98ae884c09aef38b"
        assert paper.authors == ["Ben Green", "Terence Tao"]
        assert paper.year == 2008
        assert paper.arxiv_id == "math/0404188"
        assert paper.doi == "10.4007/annals.2008.167.481"
        assert paper.citation_count == 1234

    def test_parse_handles_missing_authors(self) -> None:
        """Handles missing authors gracefully."""
        raw = {"paperId": "abc", "title": "Test"}
        paper = S2Paper.from_api_response(raw)
        assert paper.authors == []

    def test_parse_handles_missing_external_ids(self) -> None:
        """Handles missing externalIds gracefully."""
        raw = {"paperId": "abc", "title": "Test", "externalIds": None}
        paper = S2Paper.from_api_response(raw)
        assert paper.arxiv_id is None
        assert paper.doi is None

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        paper = S2Paper.from_api_response(SAMPLE_PAPER_RESPONSE)
        data = paper.to_dict()

        assert data["s2_id"] == "649def34f8be52c8b66281af98ae884c09aef38b"
        assert (
            data["title"]
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert data["authors"] == ["Ben Green", "Terence Tao"]

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        paper = S2Paper.from_api_response(SAMPLE_PAPER_RESPONSE)
        data = paper.to_dict()
        restored = S2Paper.from_dict(data)

        assert restored.s2_id == paper.s2_id
        assert restored.title == paper.title
        assert restored.authors == paper.authors


class TestCitationContext:
    """Tests for CitationContext dataclass."""

    def test_parse_from_api_response(self) -> None:
        """Parses citation from API response."""
        raw = SAMPLE_CITATIONS_RESPONSE["data"][0]
        citation = CitationContext.from_api_response(raw)

        assert citation.citing_paper_id == "abc123"
        assert citation.citing_paper_title == "New bounds on sum-free sets"
        assert citation.citing_paper_year == 2015
        assert citation.intents == ["methodology"]
        assert len(citation.contexts) == 1
        assert "density increment strategy" in citation.contexts[0]

    def test_parse_handles_missing_intents(self) -> None:
        """Handles missing intents gracefully."""
        raw = {
            "citingPaper": {"paperId": "abc", "title": "Test"},
            "contexts": ["Some context"],
        }
        citation = CitationContext.from_api_response(raw)
        assert citation.intents == []

    def test_parse_handles_missing_contexts(self) -> None:
        """Handles missing contexts gracefully."""
        raw = {
            "citingPaper": {"paperId": "abc", "title": "Test"},
            "intents": ["background"],
        }
        citation = CitationContext.from_api_response(raw)
        assert citation.contexts == []

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        raw = SAMPLE_CITATIONS_RESPONSE["data"][0]
        citation = CitationContext.from_api_response(raw)
        data = citation.to_dict()

        assert data["citing_paper_id"] == "abc123"
        assert data["intents"] == ["methodology"]

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        raw = SAMPLE_CITATIONS_RESPONSE["data"][0]
        citation = CitationContext.from_api_response(raw)
        data = citation.to_dict()
        restored = CitationContext.from_dict(data)

        assert restored.citing_paper_id == citation.citing_paper_id
        assert restored.intents == citation.intents


class TestS2Reference:
    """Tests for S2Reference dataclass."""

    def test_parse_from_api_response(self) -> None:
        """Parses reference from API response."""
        raw = SAMPLE_REFERENCES_RESPONSE["data"][0]
        ref = S2Reference.from_api_response(raw)

        assert ref.cited_paper_id == "ref123"
        assert ref.cited_paper_title == "Szemeredi's theorem"
        assert ref.cited_paper_year == 1975
        assert ref.intents == ["background", "methodology"]
        assert len(ref.contexts) == 1

    def test_parse_handles_empty_contexts(self) -> None:
        """Handles empty contexts list."""
        raw = SAMPLE_REFERENCES_RESPONSE["data"][1]
        ref = S2Reference.from_api_response(raw)
        assert ref.contexts == []

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        raw = SAMPLE_REFERENCES_RESPONSE["data"][0]
        ref = S2Reference.from_api_response(raw)
        data = ref.to_dict()

        assert data["cited_paper_id"] == "ref123"
        assert data["intents"] == ["background", "methodology"]

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        raw = SAMPLE_REFERENCES_RESPONSE["data"][0]
        ref = S2Reference.from_api_response(raw)
        data = ref.to_dict()
        restored = S2Reference.from_dict(data)

        assert restored.cited_paper_id == ref.cited_paper_id
        assert restored.intents == ref.intents


class TestSemanticScholarClient:
    """Tests for Semantic Scholar API client."""

    def test_normalize_identifier_doi(self) -> None:
        """Normalizes DOI identifier."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        assert client._normalize_identifier("10.1234/example") == "10.1234/example"

    def test_normalize_identifier_s2_id(self) -> None:
        """Normalizes S2 paper ID (40-char hex)."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        s2_id = "649def34f8be52c8b66281af98ae884c09aef38b"
        assert client._normalize_identifier(s2_id) == s2_id

    def test_normalize_identifier_legacy_arxiv(self) -> None:
        """Normalizes legacy arXiv ID with ARXIV: prefix."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        assert client._normalize_identifier("math/0404188") == "ARXIV:math/0404188"

    def test_normalize_identifier_modern_arxiv(self) -> None:
        """Normalizes modern arXiv ID with ARXIV: prefix."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        assert client._normalize_identifier("2301.00001") == "ARXIV:2301.00001"

    @responses.activate
    def test_get_paper_success(self) -> None:
        """Gets paper successfully."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        paper = client.get_paper("10.4007/annals.2008.167.481", use_cache=False)

        assert paper is not None
        assert (
            paper.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(responses.calls) == 1

        # Verify headers
        request = responses.calls[0].request
        assert request.headers["x-api-key"] == "test-key"

    @responses.activate
    def test_get_paper_not_found(self) -> None:
        """Returns None when paper not found."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/nonexistent",
            json={"error": "Not found"},
            status=404,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        paper = client.get_paper("10.1234/nonexistent", use_cache=False)

        assert paper is None

    @responses.activate
    def test_get_paper_without_api_key(self) -> None:
        """Works without API key (unauthenticated)."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )

        config = S2Config(api_key=None)
        client = SemanticScholarClient(config)
        paper = client.get_paper("10.4007/annals.2008.167.481", use_cache=False)

        assert paper is not None

        # Verify no API key in headers
        request = responses.calls[0].request
        assert "x-api-key" not in request.headers

    @responses.activate
    def test_get_citations_success(self) -> None:
        """Gets citations successfully."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        citations = client.get_citations(
            "10.4007/annals.2008.167.481", limit=10, use_cache=False
        )

        assert len(citations) == 3
        assert citations[0].citing_paper_title == "New bounds on sum-free sets"
        assert citations[0].intents == ["methodology"]

    @responses.activate
    def test_get_citations_with_arxiv_id(self) -> None:
        """Gets citations using arXiv ID."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/ARXIV:math/0404188/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        citations = client.get_citations("math/0404188", limit=10, use_cache=False)

        assert len(citations) == 3

    @responses.activate
    def test_get_citations_not_found(self) -> None:
        """Returns empty list when paper not found."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/nonexistent/citations",
            json={"error": "Not found"},
            status=404,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        citations = client.get_citations("10.1234/nonexistent", use_cache=False)

        assert citations == []

    @responses.activate
    def test_get_references_success(self) -> None:
        """Gets references successfully."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481/references",
            json=SAMPLE_REFERENCES_RESPONSE,
            status=200,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        refs = client.get_references(
            "10.4007/annals.2008.167.481", limit=10, use_cache=False
        )

        assert len(refs) == 2
        assert refs[0].cited_paper_title == "Szemeredi's theorem"
        assert refs[0].intents == ["background", "methodology"]

    @responses.activate
    def test_get_references_not_found(self) -> None:
        """Returns empty list when paper not found."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.1234/nonexistent/references",
            json={"error": "Not found"},
            status=404,
        )

        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)
        refs = client.get_references("10.1234/nonexistent", use_cache=False)

        assert refs == []

    @responses.activate
    def test_handles_rate_limit(self) -> None:
        """Retries on 429 rate limit errors."""
        # First request returns 429, second succeeds
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            status=429,
            headers={"Retry-After": "0.1"},
        )
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )

        config = S2Config(api_key="test-key", max_retries=3)
        client = SemanticScholarClient(config)
        paper = client.get_paper("10.4007/annals.2008.167.481", use_cache=False)

        assert paper is not None
        assert len(responses.calls) == 2

    @responses.activate
    def test_raises_on_401(self) -> None:
        """Raises HTTPError on authentication error."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json={"error": "Invalid API key"},
            status=401,
        )

        config = S2Config(api_key="bad-key")
        client = SemanticScholarClient(config)

        with pytest.raises(requests.HTTPError):
            client.get_paper("10.4007/annals.2008.167.481", use_cache=False)


class TestSemanticScholarClientCaching:
    """Tests for S2 client caching."""

    def test_cache_key_generation(self) -> None:
        """Generates consistent cache keys."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        key1 = client._cache_key("paper", "10.1234/example")
        key2 = client._cache_key("paper", "10.1234/example")
        key3 = client._cache_key("paper", "10.1234/different")
        key4 = client._cache_key("citations", "10.1234/example")

        assert key1 == key2
        assert key1 != key3
        assert key1 != key4  # Different endpoints produce different keys
        # Verify it's a SHA256 hash
        assert len(key1) == 64

    def test_cache_key_normalized(self) -> None:
        """Cache keys are normalized (lowercase, stripped)."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        key1 = client._cache_key("paper", "10.1234/Example")
        key2 = client._cache_key("paper", "  10.1234/example  ")

        assert key1 == key2

    @responses.activate
    def test_caches_paper_response(self, tmp_path: Path) -> None:
        """Caches paper response to disk."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "s2_cache"
        config = S2Config(api_key="test-key", cache_path=cache_path)
        client = SemanticScholarClient(config)

        paper = client.get_paper("10.4007/annals.2008.167.481")
        assert paper is not None

        # Verify cache file exists
        cache_key = client._cache_key("paper", "10.4007/annals.2008.167.481")
        cache_file = cache_path / f"paper_{cache_key}.json"
        assert cache_file.exists()

        # Verify cache content
        with cache_file.open() as f:
            cached = json.load(f)
        assert cached["paper"]["s2_id"] == "649def34f8be52c8b66281af98ae884c09aef38b"
        assert "cached_at" in cached

    @responses.activate
    def test_returns_cached_paper_response(self, tmp_path: Path) -> None:
        """Returns cached response without network call."""
        cache_path = tmp_path / "s2_cache"
        config = S2Config(api_key="test-key", cache_path=cache_path)
        client = SemanticScholarClient(config)

        # Pre-populate cache
        cache_key = client._cache_key("paper", "cached-doi")
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"paper_{cache_key}.json"

        cached_data = {
            "paper": {
                "s2_id": "cached123",
                "title": "Cached Paper",
                "authors": ["Test Author"],
                "year": 2024,
                "doi": "cached-doi",
                "arxiv_id": None,
                "citation_count": 100,
            },
            "cached_at": time.time(),
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # No network mock - should use cache
        paper = client.get_paper("cached-doi")

        assert paper is not None
        assert paper.title == "Cached Paper"

    @responses.activate
    def test_caches_citations_response(self, tmp_path: Path) -> None:
        """Caches citations response to disk."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/10.4007/annals.2008.167.481/citations",
            json=SAMPLE_CITATIONS_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "s2_cache"
        config = S2Config(api_key="test-key", cache_path=cache_path)
        client = SemanticScholarClient(config)

        citations = client.get_citations("10.4007/annals.2008.167.481", limit=10)
        assert len(citations) == 3

        # Verify cache file exists
        cache_key = client._cache_key(
            "citations", "10.4007/annals.2008.167.481:limit=10"
        )
        cache_file = cache_path / f"citations_{cache_key}.json"
        assert cache_file.exists()

    @responses.activate
    def test_cache_expiry(self, tmp_path: Path) -> None:
        """Fetches fresh data when cache is expired."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/expired-doi",
            json=SAMPLE_PAPER_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "s2_cache"
        # 1 day TTL for faster test
        config = S2Config(api_key="test-key", cache_path=cache_path, cache_ttl_days=1)
        client = SemanticScholarClient(config)

        # Pre-populate cache with old timestamp (2 days ago)
        cache_key = client._cache_key("paper", "expired-doi")
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"paper_{cache_key}.json"

        old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
        cached_data = {
            "paper": {
                "s2_id": "old123",
                "title": "Old Paper",
                "authors": [],
                "year": 2020,
                "doi": None,
                "arxiv_id": None,
                "citation_count": 0,
            },
            "cached_at": old_time,
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # Should fetch fresh data
        paper = client.get_paper("expired-doi")

        assert paper is not None
        assert (
            paper.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(responses.calls) == 1

    def test_get_cache_path(self, tmp_path: Path) -> None:
        """Returns correct cache path for an endpoint."""
        cache_path = tmp_path / "s2_cache"
        config = S2Config(api_key="test-key", cache_path=cache_path)
        client = SemanticScholarClient(config)

        path = client.get_cache_path("paper", "test-id")

        assert path.parent == cache_path
        assert path.suffix == ".json"
        assert path.name.startswith("paper_")
        assert len(path.stem.split("_")[1]) == 64  # SHA256 hash

    @responses.activate
    def test_caches_not_found_paper(self, tmp_path: Path) -> None:
        """Caches 'not found' result to avoid repeated lookups."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/nonexistent-doi",
            json={"error": "Not found"},
            status=404,
        )

        cache_path = tmp_path / "s2_cache"
        config = S2Config(api_key="test-key", cache_path=cache_path)
        client = SemanticScholarClient(config)

        # First call - makes network request
        paper1 = client.get_paper("nonexistent-doi")
        assert paper1 is None
        assert len(responses.calls) == 1

        # Second call - uses cache, no network request
        paper2 = client.get_paper("nonexistent-doi")
        assert paper2 is None
        assert len(responses.calls) == 1  # Still 1, not 2


class TestSemanticScholarClientRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limiter_delay_unauthenticated(self) -> None:
        """Uses 3s delay without API key."""
        config = S2Config(api_key=None)
        client = SemanticScholarClient(config)

        assert client._rate_limiter.delay_seconds == 3.0

    def test_rate_limiter_delay_authenticated(self) -> None:
        """Uses 1s delay with API key."""
        config = S2Config(api_key="test-key")
        client = SemanticScholarClient(config)

        assert client._rate_limiter.delay_seconds == 1.0
