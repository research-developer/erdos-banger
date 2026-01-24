"""Exa Research API client for agentic literature synthesis.

# exempt: DEBT-093

Exa (https://exa.ai/) provides structured research queries with automatic
source clustering and summarization for academic and research content.

API Reference: https://docs.exa.ai/
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests

from erdos.core.config import AppConfig
from erdos.core.constants import DEFAULT_HTTP_TIMEOUT
from erdos.core.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


# Default cache location
DEFAULT_CACHE_PATH = Path("literature/cache/exa")
DEFAULT_CACHE_TTL_HOURS = 24


@dataclass(frozen=True)
class ExaConfig:
    """Exa client configuration."""

    api_key: str | None = None
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_retries: int = 3
    cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS
    cache_path: Path = field(default=DEFAULT_CACHE_PATH)

    @classmethod
    def from_env(cls) -> ExaConfig:
        """Create config from environment variables via AppConfig.

        Uses centralized AppConfig for environment variable reads (DEBT-075).

        Returns:
            ExaConfig instance with values from AppConfig.
        """
        app_config = AppConfig.from_env()
        api_key = app_config.exa_api_key or None

        return cls(
            api_key=api_key,
            cache_ttl_hours=app_config.exa_cache_ttl_hours,
        )


@dataclass
class ExaSource:
    """A source returned from Exa search results."""

    title: str
    url: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    relevance: str | None = None
    score: float | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ExaSource:
        """Parse source from Exa API response.

        Args:
            data: Raw source dict from API.

        Returns:
            ExaSource instance.
        """
        url = data.get("url", "")
        title = data.get("title", "")

        # Parse authors (comma-separated string)
        authors: list[str] = []
        author_str = data.get("author", "")
        if author_str:
            authors = [a.strip() for a in author_str.split(",") if a.strip()]

        # Parse year from publishedDate
        year = None
        pub_date = data.get("publishedDate", "")
        if pub_date:
            match = re.match(r"(\d{4})", pub_date)
            if match:
                year = int(match.group(1))

        # Extract arXiv ID from URL
        arxiv_id = _extract_arxiv_id(url)

        # Extract DOI from URL
        doi = _extract_doi(url)

        # Relevance from text snippet
        relevance = data.get("text")

        # Score
        score = data.get("score")

        return cls(
            title=title,
            url=url,
            authors=authors,
            year=year,
            arxiv_id=arxiv_id,
            doi=doi,
            relevance=relevance,
            score=score,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "title": self.title,
            "url": self.url,
            "authors": self.authors,
            "year": self.year,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "relevance": self.relevance,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExaSource:
        """Deserialize from cached dict."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            arxiv_id=data.get("arxiv_id"),
            doi=data.get("doi"),
            relevance=data.get("relevance"),
            score=data.get("score"),
        )


@dataclass
class ExaResearchResult:
    """Result from Exa research search."""

    query: str
    sources: list[ExaSource]
    answer: str | None = None
    autoprompt: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any], query: str) -> ExaResearchResult:
        """Parse result from Exa API response.

        Args:
            data: Raw API response dict.
            query: Original query string.

        Returns:
            ExaResearchResult instance.
        """
        sources = [ExaSource.from_api_response(r) for r in data.get("results", [])]
        answer = data.get("summary")
        autoprompt = data.get("autopromptString")

        return cls(
            query=query,
            sources=sources,
            answer=answer,
            autoprompt=autoprompt,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "answer": self.answer,
            "autoprompt": self.autoprompt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExaResearchResult:
        """Deserialize from cached dict."""
        sources = [ExaSource.from_dict(s) for s in data.get("sources", [])]
        return cls(
            query=data.get("query", ""),
            sources=sources,
            answer=data.get("answer"),
            autoprompt=data.get("autoprompt"),
        )


class ExaClient:
    """Client for Exa Research API.

    Provides methods to search for research content with automatic
    source clustering. Implements caching to avoid redundant API calls.
    """

    BASE_URL = "https://api.exa.ai"

    def __init__(self, config: ExaConfig | None = None):
        """Initialize client with configuration.

        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or ExaConfig.from_env()
        self._rate_limiter = RateLimiter(delay_seconds=1.0)  # 1 req/sec to be polite

    def _cache_key(self, query: str) -> str:
        """Generate cache key from query.

        Args:
            query: Search query string.

        Returns:
            SHA256 hash of normalized query.
        """
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_cache_path(self, query: str) -> Path:
        """Get cache file path for a query.

        Args:
            query: Search query string.

        Returns:
            Path to cache file.
        """
        cache_key = self._cache_key(query)
        return self.config.cache_path / f"{cache_key}.json"

    def _load_from_cache(self, query: str) -> ExaResearchResult | None:
        """Load result from cache if valid.

        Args:
            query: Search query string.

        Returns:
            Cached result if valid and not expired, None otherwise.
        """
        cache_file = self.get_cache_path(query)
        if not cache_file.exists():
            return None

        try:
            with cache_file.open() as f:
                data = json.load(f)

            # Check TTL
            cached_at = data.get("cached_at", 0)
            ttl_seconds = self.config.cache_ttl_hours * 60 * 60
            if time.time() - cached_at > ttl_seconds:
                logger.debug("Cache expired for query: %s", query)
                return None

            logger.debug("Cache hit for query: %s", query)
            return ExaResearchResult.from_dict(data)

        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cache for query %s: %s", query, e)
            return None

    def _save_to_cache(self, result: ExaResearchResult) -> None:
        """Save result to cache.

        Args:
            result: Search result to cache.
        """
        cache_file = self.get_cache_path(result.query)

        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = result.to_dict()
            data["cached_at"] = time.time()

            with cache_file.open("w") as f:
                json.dump(data, f, indent=2)

            logger.debug("Cached result for query: %s", result.query)

        except OSError as e:
            logger.warning("Failed to cache result for query %s: %s", result.query, e)

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        use_cache: bool = True,
    ) -> ExaResearchResult:
        """Search for research content.

        Args:
            query: Natural language search query.
            max_results: Maximum number of sources to return.
            use_cache: Whether to use cached results.

        Returns:
            ExaResearchResult with sources.

        Raises:
            ValueError: If API key is not set.
            requests.HTTPError: On HTTP errors.
            json.JSONDecodeError: If response is invalid JSON.
        """
        if not self.config.api_key:
            raise ValueError("EXA_API_KEY not set")

        # Check cache first
        if use_cache:
            cached = self._load_from_cache(query)
            if cached is not None:
                return cached

        # Make API request
        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/search"
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "numResults": max_results,
            "type": "neural",
            "useAutoprompt": True,
            "contents": {
                "text": {"maxCharacters": 500},
            },
        }

        response = self._post_with_retry(url, headers=headers, payload=payload)

        try:
            data = response.json()
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
            snippet = response.text[:200].replace("\n", "\\n")
            logger.error(
                "Exa invalid JSON for %s (status %d): %s",
                url,
                response.status_code,
                snippet,
            )
            raise

        result = ExaResearchResult.from_api_response(data, query=query)

        # Cache result
        if use_cache:
            self._save_to_cache(result)

        return result

    def _post_with_retry(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> requests.Response:
        """POST with retry logic for transient failures.

        Args:
            url: API endpoint URL.
            headers: HTTP headers.
            payload: JSON payload.

        Returns:
            requests.Response on success.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
            requests.Timeout: After all retries exhausted.
        """
        last_error: Exception | None = None
        last_response: requests.Response | None = None
        retryable_codes = {429, 500, 502, 503, 504}

        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout,
                )

                if response.status_code in retryable_codes:
                    last_response = response
                    if attempt < self.config.max_retries - 1:
                        delay = self._get_retry_delay(attempt, response)
                        logger.debug(
                            "Retry %d/%d for %s: HTTP %d, waiting %.1fs",
                            attempt + 1,
                            self.config.max_retries,
                            url,
                            response.status_code,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    response.raise_for_status()

                response.raise_for_status()
                return response

            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self._get_retry_delay(attempt, None)
                    logger.debug(
                        "Retry %d/%d for %s: %s, waiting %.1fs",
                        attempt + 1,
                        self.config.max_retries,
                        url,
                        type(e).__name__,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise

            except requests.HTTPError:
                raise

        if last_error is not None:
            raise last_error
        if last_response is not None:
            last_response.raise_for_status()
        raise requests.RequestException("Max retries exceeded")

    def _get_retry_delay(
        self, attempt: int, response: requests.Response | None
    ) -> float:
        """Calculate retry delay with exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed).
            response: HTTP response if available.

        Returns:
            Delay in seconds.
        """
        max_delay = 30.0

        # Check Retry-After header for 429
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), max_delay)
                except ValueError:
                    pass

        # Exponential backoff: 2^attempt
        delay = 2.0 * (2**attempt)
        return float(min(delay, max_delay))


def _extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL.

    Args:
        url: URL that may contain arXiv ID.

    Returns:
        arXiv ID without version suffix, or None.
    """
    # Match patterns like:
    # https://arxiv.org/abs/2301.00001
    # https://arxiv.org/abs/2301.00001v3
    # https://arxiv.org/abs/math/0404188
    # https://arxiv.org/abs/math/0404188v2
    match = re.search(
        r"arxiv\.org/(?:abs|pdf)/([a-z-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?",
        url,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def _extract_doi(url: str) -> str | None:
    """Extract DOI from URL.

    Args:
        url: URL that may contain DOI.

    Returns:
        DOI string, or None.
    """
    # Match patterns like:
    # https://doi.org/10.1234/example
    # https://doi.org/10.1007%2Fs00222-016-0678-7
    match = re.search(r"doi\.org/(.+?)(?:\?|$)", url)
    if match:
        doi = unquote(match.group(1))
        return doi
    return None
