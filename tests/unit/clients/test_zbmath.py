"""Unit tests for zbMATH Open API client."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import unquote

import pytest
import requests
import responses

from erdos.core.clients.zbmath import (
    MSCCode,
    ZbMathClient,
    ZbMathConfig,
    ZbMathEntry,
)


# Sample zbMATH API response (based on real API response for Green-Tao paper)
SAMPLE_DOCUMENT_RESPONSE: dict[str, Any] = {
    "result": {
        "id": 5578697,
        "identifier": "1191.11025",
        "title": {
            "title": "The primes contain arbitrarily long arithmetic progressions",
            "subtitle": None,
            "addition": None,
            "original": None,
        },
        "year": "2008",
        "contributors": {
            "authors": [
                {"name": "Green, Ben", "codes": ["green.ben"], "checked": "1"},
                {"name": "Tao, Terence", "codes": ["tao.terence-c"], "checked": "1"},
            ],
            "editors": [],
        },
        "msc": [
            {"code": "11B25", "scheme": "msc2020", "text": "Arithmetic progressions"},
            {
                "code": "11N13",
                "scheme": "msc2020",
                "text": "Primes in congruence classes",
            },
            {"code": "11A41", "scheme": "msc2020", "text": "Primes"},
        ],
        "keywords": ["primes", "arithmetic progressions", "density"],
        "links": [
            {
                "identifier": "10.4007/annals.2008.167.481",
                "type": "doi",
                "url": "https://doi.org/10.4007/annals.2008.167.481",
            },
            {
                "identifier": "math/0404188",
                "type": "arxiv",
                "url": "https://arxiv.org/abs/math/0404188",
            },
        ],
        "source": {
            "series": [
                {
                    "title": "Annals of Mathematics. Second Series",
                    "short_title": "Ann. Math. (2)",
                    "volume": "167",
                    "issue": "2",
                    "year": "2008",
                }
            ],
            "pages": "481-547",
        },
        "editorial_contributions": [
            {
                "contribution_type": "review",
                "language": "English",
                "reviewer": {
                    "name": "Tom Sanders",
                    "reviewer_id": "11861",
                    "sign": "Tom Sanders (Cambridge)",
                },
                "text": "This paper needs little introduction: in 2004, the authors proved that the primes contain arbitrarily long arithmetic progressions, a startling result...",
            }
        ],
        "zbmath_url": "https://zbmath.org/5578697",
    },
    "status": {
        "execution": "successful request",
        "execution_bool": True,
        "status_code": 200,
    },
}

# Sample search response (multiple results)
SAMPLE_SEARCH_RESPONSE: dict[str, Any] = {
    "result": [
        {
            "id": 3227181,
            "identifier": "0141.04405",
            "title": {
                "title": "Sequences. Vol. I",
                "subtitle": None,
            },
            "year": "1966",
            "contributors": {
                "authors": [
                    {"name": "Halberstam, H.", "codes": ["halberstam.heini"]},
                    {"name": "Roth, Klaus F.", "codes": ["roth.klaus-f"]},
                ],
                "editors": [],
            },
            "msc": [
                {
                    "code": "11B05",
                    "scheme": "msc2020",
                    "text": "Density, gaps, topology",
                },
                {"code": "11Bxx", "scheme": "msc2020", "text": "Sequences and sets"},
            ],
            "keywords": ["sequences", "sieve methods"],
            "links": [],
            "source": {"series": [], "pages": None},
            "editorial_contributions": [],
            "zbmath_url": "https://zbmath.org/3227181",
        },
        {
            "id": 3663470,
            "identifier": "0426.28014",
            "title": {
                "title": "An ergodic Szemerédi theorem for commuting transformations",
                "subtitle": None,
            },
            "year": "1978",
            "contributors": {
                "authors": [
                    {"name": "Furstenberg, H.", "codes": ["furstenberg.hillel"]},
                    {"name": "Katznelson, Y.", "codes": ["katznelson.yitzhak"]},
                ],
                "editors": [],
            },
            "msc": [
                {
                    "code": "11B05",
                    "scheme": "msc2020",
                    "text": "Density, gaps, topology",
                },
                {
                    "code": "11B25",
                    "scheme": "msc2020",
                    "text": "Arithmetic progressions",
                },
            ],
            "keywords": ["ergodic Szemerédi theorem", "Poincaré recurrence theorem"],
            "links": [
                {
                    "identifier": "10.1007/BF02790016",
                    "type": "doi",
                    "url": "https://doi.org/10.1007/BF02790016",
                }
            ],
            "source": {"series": [], "pages": "275-291"},
            "editorial_contributions": [
                {
                    "contribution_type": "review",
                    "text": "The authors prove the measure-theoretic analogue...",
                }
            ],
            "zbmath_url": "https://zbmath.org/3663470",
        },
    ],
    "status": {
        "execution": "successful request",
        "execution_bool": True,
        "status_code": 200,
        "nr_total_results": 1247,
        "nr_request_results": 2,
    },
}


class TestZbMathConfig:
    """Tests for ZbMathConfig."""

    def test_default_config(self) -> None:
        """Config has sensible defaults."""
        config = ZbMathConfig()
        assert config.mailto is None
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_ttl_days == 30
        assert config.cache_path == Path("literature/cache/zbmath")

    def test_from_env_with_mailto(self) -> None:
        """Config loads ERDOS_MAILTO from environment."""
        with patch.dict(
            "os.environ", {"ERDOS_MAILTO": "test@example.com"}, clear=False
        ):
            config = ZbMathConfig.from_env()
            assert config.mailto == "test@example.com"

    def test_from_env_with_cache_ttl(self) -> None:
        """Config loads ERDOS_ZBMATH_CACHE_TTL from environment."""
        env = {"ERDOS_ZBMATH_CACHE_TTL": "60"}
        with patch.dict("os.environ", env, clear=False):
            config = ZbMathConfig.from_env()
            assert config.cache_ttl_days == 60


class TestMSCCode:
    """Tests for MSCCode dataclass."""

    def test_msc_code_creation(self) -> None:
        """Creates MSC code with all fields."""
        msc = MSCCode(
            code="11B05",
            text="Density, gaps, topology",
            scheme="msc2020",
            primary=True,
        )
        assert msc.code == "11B05"
        assert msc.text == "Density, gaps, topology"
        assert msc.scheme == "msc2020"
        assert msc.primary is True

    def test_msc_code_defaults(self) -> None:
        """Creates MSC code with default values."""
        msc = MSCCode(code="11B05", text="Density, gaps, topology")
        assert msc.scheme == "msc2020"
        assert msc.primary is False

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        msc = MSCCode(code="11B05", text="Density, gaps, topology", primary=True)
        data = msc.to_dict()

        assert data["code"] == "11B05"
        assert data["text"] == "Density, gaps, topology"
        assert data["primary"] is True

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        data = {"code": "11B05", "text": "Density, gaps, topology", "primary": True}
        msc = MSCCode.from_dict(data)

        assert msc.code == "11B05"
        assert msc.text == "Density, gaps, topology"
        assert msc.primary is True


class TestZbMathEntry:
    """Tests for ZbMathEntry dataclass."""

    def test_parse_from_api_response(self) -> None:
        """Parses entry from API response."""
        entry = ZbMathEntry.from_api_response(SAMPLE_DOCUMENT_RESPONSE["result"])

        assert entry.zbl_id == "1191.11025"
        assert entry.internal_id == 5578697
        assert (
            entry.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert entry.authors == ["Green, Ben", "Tao, Terence"]
        assert entry.year == 2008
        assert entry.doi == "10.4007/annals.2008.167.481"
        assert entry.arxiv_id == "math/0404188"
        assert len(entry.msc) == 3
        assert entry.msc[0].code == "11B25"
        assert entry.msc[0].text == "Arithmetic progressions"
        assert entry.journal == "Ann. Math. (2)"
        assert entry.keywords == ["primes", "arithmetic progressions", "density"]
        assert entry.review_excerpt is not None
        assert "primes contain arbitrarily long" in entry.review_excerpt
        assert entry.zbmath_url == "https://zbmath.org/5578697"

    def test_parse_handles_missing_authors(self) -> None:
        """Handles missing authors gracefully."""
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
            "year": "2020",
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.authors == []

    def test_parse_handles_missing_links(self) -> None:
        """Handles missing links gracefully."""
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
            "year": "2020",
            "contributors": {"authors": []},
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.doi is None
        assert entry.arxiv_id is None

    def test_parse_handles_missing_msc(self) -> None:
        """Handles missing MSC codes gracefully."""
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
            "year": "2020",
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.msc == []

    def test_parse_handles_null_keywords(self) -> None:
        """Handles [null] keywords from API (real behavior)."""
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
            "year": "2020",
            "keywords": [None],
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.keywords == []

    def test_parse_handles_missing_year(self) -> None:
        """Handles missing year gracefully."""
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.year is None

    def test_parse_truncates_review_excerpt(self) -> None:
        """Truncates review text to ~500 chars."""
        long_review = "A" * 1000
        raw = {
            "id": 123,
            "identifier": "0001.00001",
            "title": {"title": "Test"},
            "year": "2020",
            "editorial_contributions": [
                {"contribution_type": "review", "text": long_review}
            ],
        }
        entry = ZbMathEntry.from_api_response(raw)
        assert entry.review_excerpt is not None
        assert len(entry.review_excerpt) <= 503  # 500 + "..."

    def test_to_dict(self) -> None:
        """Serializes to dict for caching."""
        entry = ZbMathEntry.from_api_response(SAMPLE_DOCUMENT_RESPONSE["result"])
        data = entry.to_dict()

        assert data["zbl_id"] == "1191.11025"
        assert data["internal_id"] == 5578697
        assert (
            data["title"]
            == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert data["authors"] == ["Green, Ben", "Tao, Terence"]
        assert len(data["msc"]) == 3
        assert data["msc"][0]["code"] == "11B25"

    def test_from_dict(self) -> None:
        """Deserializes from cached dict."""
        entry = ZbMathEntry.from_api_response(SAMPLE_DOCUMENT_RESPONSE["result"])
        data = entry.to_dict()
        restored = ZbMathEntry.from_dict(data)

        assert restored.zbl_id == entry.zbl_id
        assert restored.title == entry.title
        assert restored.authors == entry.authors
        assert len(restored.msc) == len(entry.msc)


class TestZbMathClient:
    """Tests for zbMATH API client."""

    def test_rate_limiter_delay(self) -> None:
        """Uses 2s delay for zbMATH (conservative)."""
        config = ZbMathConfig()
        client = ZbMathClient(config)

        assert client._rate_limiter.delay_seconds == 2.0

    @responses.activate
    def test_get_by_zbl_id_success(self) -> None:
        """Gets entry by zbMATH ID successfully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            json=SAMPLE_DOCUMENT_RESPONSE,
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_zbl_id("5578697", use_cache=False)

        assert entry is not None
        assert (
            entry.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_by_zbl_id_with_prefix(self) -> None:
        """Handles 'Zbl ' prefix in ID."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            json=SAMPLE_DOCUMENT_RESPONSE,
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_zbl_id("Zbl 5578697", use_cache=False)

        assert entry is not None

    @responses.activate
    def test_get_by_zbl_id_with_identifier(self) -> None:
        """Handles zbMATH identifier format (e.g., '1191.11025')."""
        # zbMATH API returns 404 for identifiers via document endpoint
        # Need to use search endpoint instead
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_DOCUMENT_RESPONSE["result"]], "status": {}},
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_zbl_id("1191.11025", use_cache=False)

        assert entry is not None
        assert entry.zbl_id == "1191.11025"

    @responses.activate
    def test_get_by_zbl_id_not_found(self) -> None:
        """Returns None when entry not found."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/99999999",
            json={
                "result": None,
                "status": {"execution_bool": False, "status_code": 404},
            },
            status=404,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_zbl_id("99999999", use_cache=False)

        assert entry is None

    @responses.activate
    def test_get_by_doi_success(self) -> None:
        """Gets entry by DOI successfully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_DOCUMENT_RESPONSE["result"]], "status": {}},
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_doi("10.4007/annals.2008.167.481", use_cache=False)

        assert entry is not None
        assert entry.doi == "10.4007/annals.2008.167.481"

        # Verify search query (URL-decoded)
        request = responses.calls[0].request
        assert "doi:10.4007/annals.2008.167.481" in unquote(request.url or "")

    @responses.activate
    def test_get_by_doi_not_found(self) -> None:
        """Returns None when DOI not found."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [], "status": {}},
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_doi("10.1234/nonexistent", use_cache=False)

        assert entry is None

    @responses.activate
    def test_get_by_doi_404(self) -> None:
        """Returns None when API returns 404 for DOI lookup."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"error": "Not found"},
            status=404,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entry = client.get_by_doi("10.9999/nonexistent.paper", use_cache=False)

        assert entry is None

    @responses.activate
    def test_search_by_msc_success(self) -> None:
        """Searches by MSC code successfully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entries = client.search_by_msc("11B05", limit=20, use_cache=False)

        assert len(entries) == 2
        assert entries[0].title == "Sequences. Vol. I"
        assert any(msc.code == "11B05" for msc in entries[0].msc)

        # Verify search query (URL-decoded)
        request = responses.calls[0].request
        assert "cc:11B05" in unquote(request.url or "")

    @responses.activate
    def test_search_by_msc_with_year_range(self) -> None:
        """Searches by MSC code with year filter."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json=SAMPLE_SEARCH_RESPONSE,
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entries = client.search_by_msc(
            "11B05", year_min=2000, year_max=2020, use_cache=False
        )

        assert len(entries) == 2

        # Verify year filter in query (URL-decoded)
        request = responses.calls[0].request
        assert "py:2000-2020" in unquote(request.url or "")

    @responses.activate
    def test_search_by_msc_empty_results(self) -> None:
        """Returns empty list when no results."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [], "status": {}},
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entries = client.search_by_msc("99Z99", use_cache=False)

        assert entries == []

    @responses.activate
    def test_search_by_title_success(self) -> None:
        """Searches by title keywords successfully."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/_search",
            json={"result": [SAMPLE_DOCUMENT_RESPONSE["result"]], "status": {}},
            status=200,
        )

        config = ZbMathConfig()
        client = ZbMathClient(config)
        entries = client.search_by_title(
            "primes arithmetic progressions", use_cache=False
        )

        assert len(entries) == 1
        assert "primes" in entries[0].title.lower()

        # Verify title search query (URL-decoded)
        request = responses.calls[0].request
        assert "ti:" in unquote(request.url or "")

    @responses.activate
    def test_handles_rate_limit(self) -> None:
        """Retries on 429 rate limit errors."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            status=429,
            headers={"Retry-After": "0.1"},
        )
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            json=SAMPLE_DOCUMENT_RESPONSE,
            status=200,
        )

        config = ZbMathConfig(max_retries=3)
        client = ZbMathClient(config)
        entry = client.get_by_zbl_id("5578697", use_cache=False)

        assert entry is not None
        assert len(responses.calls) == 2

    @responses.activate
    def test_raises_on_server_error(self) -> None:
        """Raises HTTPError on 500 errors after retries."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            status=500,
        )
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            status=500,
        )
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            status=500,
        )

        config = ZbMathConfig(max_retries=3)
        client = ZbMathClient(config)

        with pytest.raises(requests.HTTPError):
            client.get_by_zbl_id("5578697", use_cache=False)


class TestZbMathClientCaching:
    """Tests for zbMATH client caching."""

    def test_cache_key_generation(self) -> None:
        """Generates consistent cache keys."""
        config = ZbMathConfig()
        client = ZbMathClient(config)

        key1 = client._cache_key("zbl", "5578697")
        key2 = client._cache_key("zbl", "5578697")
        key3 = client._cache_key("zbl", "1234567")
        key4 = client._cache_key("doi", "5578697")

        assert key1 == key2
        assert key1 != key3
        assert key1 != key4  # Different endpoints produce different keys
        assert len(key1) == 64  # SHA256 hash

    def test_cache_key_normalized(self) -> None:
        """Cache keys are normalized (lowercase, stripped)."""
        config = ZbMathConfig()
        client = ZbMathClient(config)

        key1 = client._cache_key("zbl", "Zbl 5578697")
        key2 = client._cache_key("zbl", "  5578697  ")

        # Both normalize to just the ID
        assert key1 == key2

    @responses.activate
    def test_caches_entry_response(self, tmp_path: Path) -> None:
        """Caches entry response to disk."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/5578697",
            json=SAMPLE_DOCUMENT_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        entry = client.get_by_zbl_id("5578697")
        assert entry is not None

        # Verify cache file exists
        cache_key = client._cache_key("zbl", "5578697")
        cache_file = cache_path / f"zbl_{cache_key}.json"
        assert cache_file.exists()

        # Verify cache content
        with cache_file.open() as f:
            cached = json.load(f)
        assert cached["entry"]["zbl_id"] == "1191.11025"
        assert "cached_at" in cached

    @responses.activate
    def test_returns_cached_entry_response(self, tmp_path: Path) -> None:
        """Returns cached response without network call."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        # Pre-populate cache
        cache_key = client._cache_key("zbl", "cached-id")
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"zbl_{cache_key}.json"

        cached_data = {
            "entry": {
                "zbl_id": "cached123",
                "internal_id": 123,
                "title": "Cached Paper",
                "authors": ["Test Author"],
                "year": 2024,
                "doi": None,
                "arxiv_id": None,
                "journal": None,
                "msc": [],
                "keywords": [],
                "review_excerpt": None,
                "zbmath_url": "https://zbmath.org/123",
            },
            "cached_at": time.time(),
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # No network mock - should use cache
        entry = client.get_by_zbl_id("cached-id")

        assert entry is not None
        assert entry.title == "Cached Paper"

    @responses.activate
    def test_cache_expiry(self, tmp_path: Path) -> None:
        """Fetches fresh data when cache is expired."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/expired-id",
            json=SAMPLE_DOCUMENT_RESPONSE,
            status=200,
        )

        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path, cache_ttl_days=1)
        client = ZbMathClient(config)

        # Pre-populate cache with old timestamp (2 days ago)
        cache_key = client._cache_key("zbl", "expired-id")
        cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = cache_path / f"zbl_{cache_key}.json"

        old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
        cached_data = {
            "entry": {
                "zbl_id": "old123",
                "internal_id": 123,
                "title": "Old Paper",
                "authors": [],
                "year": 2020,
                "doi": None,
                "arxiv_id": None,
                "journal": None,
                "msc": [],
                "keywords": [],
                "review_excerpt": None,
                "zbmath_url": None,
            },
            "cached_at": old_time,
        }
        with cache_file.open("w") as f:
            json.dump(cached_data, f)

        # Should fetch fresh data
        entry = client.get_by_zbl_id("expired-id")

        assert entry is not None
        assert (
            entry.title == "The primes contain arbitrarily long arithmetic progressions"
        )
        assert len(responses.calls) == 1

    def test_get_cache_path(self, tmp_path: Path) -> None:
        """Returns correct cache path for an endpoint."""
        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        path = client.get_cache_path("zbl", "test-id")

        assert path.parent == cache_path
        assert path.suffix == ".json"
        assert path.name.startswith("zbl_")
        assert len(path.stem.split("_")[1]) == 64  # SHA256 hash

    @responses.activate
    def test_caches_not_found_entry(self, tmp_path: Path) -> None:
        """Caches 'not found' result to avoid repeated lookups."""
        responses.add(
            responses.GET,
            "https://api.zbmath.org/v1/document/nonexistent",
            json={"result": None, "status": {"status_code": 404}},
            status=404,
        )

        cache_path = tmp_path / "zbmath_cache"
        config = ZbMathConfig(cache_path=cache_path)
        client = ZbMathClient(config)

        # First call - makes network request
        entry1 = client.get_by_zbl_id("nonexistent")
        assert entry1 is None
        assert len(responses.calls) == 1

        # Second call - uses cache, no network request
        entry2 = client.get_by_zbl_id("nonexistent")
        assert entry2 is None
        assert len(responses.calls) == 1  # Still 1, not 2
