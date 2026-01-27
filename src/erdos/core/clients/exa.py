"""Exa Research API client for agentic literature synthesis.

Exa (https://exa.ai/) provides structured research queries with automatic
source clustering and summarization for academic and research content.

API Reference: https://docs.exa.ai/
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests

from erdos.core.clients.cache import FileCache, make_cache_key
from erdos.core.config import AppConfig
from erdos.core.constants import DEFAULT_HTTP_TIMEOUT, RETRY_MAX_ATTEMPTS
from erdos.core.rate_limiter import RateLimiter
from erdos.core.retry import post_with_retry


logger = logging.getLogger(__name__)


# Default cache location
DEFAULT_CACHE_PATH = Path("literature/cache/exa")
DEFAULT_CACHE_TTL_HOURS = 24


@dataclass(frozen=True)
class ExaConfig:
    """Exa client configuration."""

    api_key: str | None = None
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_retries: int = RETRY_MAX_ATTEMPTS
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
            cache_path=(
                app_config.exa_cache_path
                if app_config.exa_cache_path
                else DEFAULT_CACHE_PATH
            ),
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

    @property
    def display_title(self) -> str:
        """Best-effort non-empty title for display/UX.

        Exa frequently returns empty titles for PDF sources; this provides a
        stable fallback so UIs don't need to special-case empty strings.
        """
        title = self.title.strip()
        if title:
            return title
        if self.doi:
            return f"DOI {self.doi}"
        if self.arxiv_id:
            return f"arXiv {self.arxiv_id}"
        if self.url:
            return self.url
        return "Untitled"

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ExaSource:
        """Parse source from Exa API response."""
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

        return cls(
            title=title,
            url=url,
            authors=authors,
            year=year,
            arxiv_id=_extract_arxiv_id(url),
            doi=_extract_doi(url),
            relevance=data.get("text"),
            score=data.get("score"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "title": self.title,
            "display_title": self.display_title,
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

    @classmethod
    def from_api_response(cls, data: dict[str, Any], query: str) -> ExaResearchResult:
        """Parse result from Exa API response."""
        sources = [ExaSource.from_api_response(r) for r in data.get("results", [])]
        return cls(query=query, sources=sources, answer=data.get("summary"))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExaResearchResult:
        """Deserialize from cached dict."""
        sources = [ExaSource.from_dict(s) for s in data.get("sources", [])]
        return cls(
            query=data.get("query", ""),
            sources=sources,
            answer=data.get("answer"),
        )


class ExaClient:
    """Client for Exa Research API.

    Provides methods to search for research content with automatic
    source clustering. Implements caching to avoid redundant API calls.
    """

    BASE_URL = "https://api.exa.ai"

    def __init__(self, config: ExaConfig | None = None):
        """Initialize client with configuration."""
        self.config = config or ExaConfig.from_env()
        self._rate_limiter = RateLimiter(delay_seconds=1.0)
        self._cache = FileCache(
            cache_path=self.config.cache_path,
            ttl_seconds=self.config.cache_ttl_hours * 60 * 60,
        )

    def _make_cache_key(self, query: str, *, max_results: int) -> str:
        """Generate cache key from request parameters."""
        return make_cache_key(query, f"max_results={max_results}")

    def get_cache_path(self, query: str, *, max_results: int) -> Path:
        """Get cache file path for a query (for testing/debugging)."""
        key = self._make_cache_key(query, max_results=max_results)
        return self._cache.get_file_path(key)

    def search_with_cache_status(
        self,
        query: str,
        *,
        max_results: int = 5,
        use_cache: bool = True,
    ) -> tuple[ExaResearchResult, bool]:
        """Search for research content and return whether served from cache."""
        if not self.config.api_key:
            raise ValueError("EXA_API_KEY not set")

        cache_key = self._make_cache_key(query, max_results=max_results)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return ExaResearchResult.from_dict(cached), True

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
            "contents": {"text": {"maxCharacters": 500}},
        }

        response = post_with_retry(
            url,
            timeout=self.config.timeout,
            json_payload=payload,
            max_attempts=self.config.max_retries,
            headers=headers,
        )

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

        if use_cache:
            self._cache.set(cache_key, result.to_dict())

        return result, False

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
        result, _cached = self.search_with_cache_status(
            query, max_results=max_results, use_cache=use_cache
        )
        return result


def _extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL."""
    match = re.search(
        r"arxiv\.org/(?:abs|pdf)/([a-z-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?",
        url,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_doi(url: str) -> str | None:
    """Extract DOI from URL."""
    match = re.search(r"doi\.org/(.+?)(?:\?|$)", url)
    if match:
        return unquote(match.group(1))
    return None
