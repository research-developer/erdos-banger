"""Unit tests for Exa Research API client."""

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

from erdos.core.clients.exa import (
    ExaClient,
    ExaConfig,
    ExaResearchResult,
    ExaSource,
)


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

SAMPLE_EXA_RESPONSE: dict[str, Any] = json.loads(
    (FIXTURES_DIR / "exa_responses" / "search_sum_free_sets.json").read_text()
)
SAMPLE_EXA_RESPONSE_WITH_SUMMARY: dict[str, Any] = json.loads(
    (
        FIXTURES_DIR / "exa_responses" / "search_sum_free_sets_with_summary.json"
    ).read_text()
)


class TestExaConfig:
    """Tests for ExaConfig."""

    def test_default_config(self) -> None:
        """Config has sensible defaults."""
        config = ExaConfig()
        assert config.api_key is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_ttl_hours == 24
        assert config.cache_path == Path("literature/cache/exa")

    def test_from_env_with_api_key(self) -> None:
        """Config loads EXA_API_KEY from environment."""
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key-123"}, clear=False):
            config = ExaConfig.from_env()
            assert config.api_key == "test-key-123"

    def test_from_env_with_cache_ttl(self) -> None:
        """Config loads ERDOS_EXA_CACHE_TTL from environment."""
        env = {"EXA_API_KEY": "key", "ERDOS_EXA_CACHE_TTL": "12"}
        with patch.dict(os.environ, env, clear=False):
            config = ExaConfig.from_env()
            assert config.cache_ttl_hours == 12

    def test_from_env_uses_app_config(self) -> None:
        """Config uses centralized AppConfig for EXA_API_KEY."""
        with patch.dict(os.environ, {"EXA_API_KEY": "app-config-key"}, clear=False):
            config = ExaConfig.from_env()
            assert config.api_key == "app-config-key"


class TestExaSource:
    """Tests for ExaSource dataclass."""

    def test_parse_from_api_response(self) -> None:
        """Parses source from API response."""
        raw = SAMPLE_EXA_RESPONSE["results"][0]
        source = ExaSource.from_api_response(raw)

        assert (
            source.title
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert source.authors == ["Ben Green", "Terence Tao"]
        assert source.year == 2008
        assert source.url == "https://arxiv.org/abs/math/0404188"
        assert source.arxiv_id == "math/0404188"
        assert source.doi is None
        assert source.relevance == "This paper proves..."
        assert source.score == 0.95

    def test_parse_extracts_doi(self) -> None:
        """Extracts DOI from URL."""
        raw = SAMPLE_EXA_RESPONSE["results"][1]
        source = ExaSource.from_api_response(raw)

        assert source.doi == "10.1007/s00222-016-0678-7"
        assert source.arxiv_id is None

    def test_parse_handles_single_author(self) -> None:
        """Handles single author without comma."""
        raw = {"author": "John Doe", "url": "https://example.com", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.authors == ["John Doe"]

    def test_parse_handles_missing_fields(self) -> None:
        """Handles missing optional fields gracefully."""
        raw = {"url": "https://example.com", "title": "Test Paper"}
        source = ExaSource.from_api_response(raw)

        assert source.title == "Test Paper"
        assert source.authors == []
        assert source.year is None
        assert source.relevance is None
        assert source.score is None


class TestExaResearchResult:
    """Tests for ExaResearchResult."""

    def test_parse_from_api_response(self) -> None:
        """Parses full result from API response."""
        result = ExaResearchResult.from_api_response(
            SAMPLE_EXA_RESPONSE, query="sum-free sets"
        )

        assert result.query == "sum-free sets"
        assert len(result.sources) == 3
        assert (
            result.sources[0].title
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert result.answer is None
        assert result.autoprompt == "Research on sum-free sets approaches"

    def test_parse_with_summary(self) -> None:
        """Parses result with summary/answer."""
        result = ExaResearchResult.from_api_response(
            SAMPLE_EXA_RESPONSE_WITH_SUMMARY, query="sum-free sets"
        )

        assert (
            result.answer == "Several approaches have been tried for sum-free sets..."
        )

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        result = ExaResearchResult.from_api_response(
            SAMPLE_EXA_RESPONSE, query="test query"
        )
        data = result.to_dict()

        assert data["query"] == "test query"
        assert len(data["sources"]) == 3
        assert "title" in data["sources"][0]

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        result = ExaResearchResult.from_api_response(
            SAMPLE_EXA_RESPONSE, query="test query"
        )
        data = result.to_dict()
        restored = ExaResearchResult.from_dict(data)

        assert restored.query == result.query
        assert len(restored.sources) == len(result.sources)
        assert restored.sources[0].title == result.sources[0].title


class TestExaClient:
    """Tests for Exa API client."""

    @responses.activate
    def test_search_success(self) -> None:
        """Searches successfully with valid API key."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        config = ExaConfig(api_key="test-key")
        client = ExaClient(config)
        # Use use_cache=False to ensure we make network requests
        result = client.search("search success test", max_results=5, use_cache=False)

        assert len(result.sources) == 3
        assert result.query == "search success test"
        assert len(responses.calls) == 1

        # Verify headers
        request = responses.calls[0].request
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["Content-Type"] == "application/json"

    @responses.activate
    def test_search_with_max_results(self) -> None:
        """Passes max_results to API."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        config = ExaConfig(api_key="test-key")
        client = ExaClient(config)
        # Use use_cache=False to ensure we make network requests
        client.search("max results test", max_results=10, use_cache=False)

        request = responses.calls[0].request
        assert request.body is not None
        body = json.loads(request.body)
        assert body["numResults"] == 10

    @responses.activate
    def test_search_missing_api_key(self) -> None:
        """Raises error when API key is missing."""
        config = ExaConfig(api_key=None)
        client = ExaClient(config)

        with pytest.raises(ValueError, match="EXA_API_KEY not set"):
            client.search("test query")

    @responses.activate
    def test_search_handles_rate_limit(self) -> None:
        """Retries on 429 rate limit errors."""
        # First request returns 429, second succeeds
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            status=429,
            headers={"Retry-After": "0.1"},
        )
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        config = ExaConfig(api_key="test-key", max_retries=3)
        client = ExaClient(config)
        # Use use_cache=False to ensure we make network requests
        result = client.search("rate limit test query", use_cache=False)

        assert len(result.sources) == 3
        assert len(responses.calls) == 2

    @responses.activate
    def test_search_raises_on_401(self) -> None:
        """Raises HTTPError on authentication error."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json={"error": "Invalid API key"},
            status=401,
        )

        config = ExaConfig(api_key="bad-key")
        client = ExaClient(config)

        with pytest.raises(requests.HTTPError):
            # Use use_cache=False to ensure we make network requests
            client.search("auth test query", use_cache=False)

    @responses.activate
    def test_search_handles_invalid_json(self) -> None:
        """Handles invalid JSON response."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            body="not valid json",
            status=200,
            content_type="text/plain",
        )

        config = ExaConfig(api_key="test-key")
        client = ExaClient(config)

        with pytest.raises(json.JSONDecodeError):
            # Use use_cache=False to ensure we make network requests
            client.search("invalid json test query", use_cache=False)


class TestExaClientCaching:
    """Tests for Exa client caching."""

    def test_cache_key_generation(self) -> None:
        """Generates consistent cache keys from query."""
        config = ExaConfig(api_key="test-key")
        client = ExaClient(config)

        key1 = client._cache_key("sum-free sets", max_results=5)
        key2 = client._cache_key("sum-free sets", max_results=5)
        key3 = client._cache_key("different query", max_results=5)
        key4 = client._cache_key("sum-free sets", max_results=10)

        assert key1 == key2
        assert key1 != key3
        assert key1 != key4
        # Verify it's a SHA256 hash
        assert len(key1) == 64

    def test_cache_key_normalized(self) -> None:
        """Cache keys are normalized (lowercase, stripped)."""
        config = ExaConfig(api_key="test-key")
        client = ExaClient(config)

        key1 = client._cache_key("Sum-Free Sets", max_results=5)
        key2 = client._cache_key("  sum-free sets  ", max_results=5)

        assert key1 == key2

    @responses.activate
    def test_caches_response(self, tmp_path: Path) -> None:
        """Caches response to disk."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "exa_cache"
        config = ExaConfig(api_key="test-key", cache_path=cache_path)
        client = ExaClient(config)

        result = client.search("test query")
        assert result is not None  # Ensure search completed

        # Verify cache file exists
        cache_key = client._cache_key("test query", max_results=5)
        cache_file = cache_path / f"{cache_key}.json"
        assert cache_file.exists()

        # Verify cache content
        with cache_file.open() as f:
            cached = json.load(f)
        assert cached["query"] == "test query"
        assert "cached_at" in cached
        assert "sources" in cached

    @responses.activate
    def test_returns_cached_response(self, tmp_path: Path) -> None:
        """Returns cached response without network call."""
        cache_path = tmp_path / "exa_cache"
        config = ExaConfig(api_key="test-key", cache_path=cache_path)
        client = ExaClient(config)

        # Pre-populate cache
        cache_key = client._cache_key("cached query", max_results=5)
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"{cache_key}.json"

        cached_data = {
            "query": "cached query",
            "sources": [
                {
                    "title": "Cached Paper",
                    "authors": ["Test Author"],
                    "year": 2024,
                    "url": "https://example.com",
                    "arxiv_id": None,
                    "doi": None,
                    "relevance": "Cached relevance",
                    "score": 0.9,
                }
            ],
            "answer": None,
            "autoprompt": None,
            "cached_at": time.time(),
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # No network mock - should use cache
        result = client.search("cached query")

        assert len(result.sources) == 1
        assert result.sources[0].title == "Cached Paper"

    @responses.activate
    def test_cache_expiry(self, tmp_path: Path) -> None:
        """Fetches fresh data when cache is expired."""
        responses.add(
            responses.POST,
            "https://api.exa.ai/search",
            json=SAMPLE_EXA_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "exa_cache"
        # 1 hour TTL for faster test
        config = ExaConfig(api_key="test-key", cache_path=cache_path, cache_ttl_hours=1)
        client = ExaClient(config)

        # Pre-populate cache with old timestamp (2 hours ago)
        cache_key = client._cache_key("expired query", max_results=5)
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"{cache_key}.json"

        old_time = time.time() - (2 * 60 * 60)  # 2 hours ago
        cached_data = {
            "query": "expired query",
            "sources": [{"title": "Old Paper", "url": "https://old.com"}],
            "answer": None,
            "autoprompt": None,
            "cached_at": old_time,
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # Should fetch fresh data
        result = client.search("expired query")

        assert len(result.sources) == 3
        assert (
            result.sources[0].title
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(responses.calls) == 1

    def test_get_cache_path(self, tmp_path: Path) -> None:
        """Returns correct cache path for a query."""
        cache_path = tmp_path / "exa_cache"
        config = ExaConfig(api_key="test-key", cache_path=cache_path)
        client = ExaClient(config)

        path = client.get_cache_path("test query", max_results=5)

        assert path.parent == cache_path
        assert path.suffix == ".json"
        assert len(path.stem) == 64  # SHA256 hash


class TestExaSourceParsing:
    """Tests for parsing various source URL formats."""

    def test_parse_arxiv_url_modern(self) -> None:
        """Parses modern arXiv URL (YYMM.NNNNN)."""
        raw = {"url": "https://arxiv.org/abs/2301.00001", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.arxiv_id == "2301.00001"

    def test_parse_arxiv_url_legacy(self) -> None:
        """Parses legacy arXiv URL (category/NNNNNNN)."""
        raw = {"url": "https://arxiv.org/abs/math/0404188", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.arxiv_id == "math/0404188"

    def test_parse_arxiv_url_with_version(self) -> None:
        """Parses arXiv URL with version suffix."""
        raw = {"url": "https://arxiv.org/abs/2301.00001v3", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        # Version stripped for canonical ID
        assert source.arxiv_id == "2301.00001"

    def test_parse_doi_url(self) -> None:
        """Parses DOI URL."""
        raw = {"url": "https://doi.org/10.1234/example.5678", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.doi == "10.1234/example.5678"

    def test_parse_doi_url_encoded(self) -> None:
        """Parses URL-encoded DOI."""
        raw = {"url": "https://doi.org/10.1007%2Fs00222-016-0678-7", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.doi == "10.1007/s00222-016-0678-7"

    def test_parse_generic_url(self) -> None:
        """Handles generic URLs without arXiv or DOI."""
        raw = {"url": "https://example.com/paper.pdf", "title": "Test"}
        source = ExaSource.from_api_response(raw)
        assert source.arxiv_id is None
        assert source.doi is None
        assert source.url == "https://example.com/paper.pdf"
