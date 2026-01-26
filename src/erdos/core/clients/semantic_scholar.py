"""Semantic Scholar API client for citation context extraction.

Semantic Scholar (https://www.semanticscholar.org/) provides citation intent
classification and in-context snippets - information not available in other APIs.

API Reference: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from erdos.core.clients.cache import FileCache, make_cache_key
from erdos.core.config import AppConfig
from erdos.core.constants import DEFAULT_HTTP_TIMEOUT, RETRY_MAX_ATTEMPTS
from erdos.core.rate_limiter import RateLimiter
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


# Default cache location and TTL
DEFAULT_CACHE_PATH = Path("literature/cache/s2")
DEFAULT_CACHE_TTL_DAYS = 7


@dataclass(frozen=True)
class S2Config:
    """Semantic Scholar client configuration."""

    api_key: str | None = None
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_retries: int = RETRY_MAX_ATTEMPTS
    cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS
    cache_path: Path = field(default=DEFAULT_CACHE_PATH)

    @classmethod
    def from_env(cls) -> S2Config:
        """Create config from environment variables via AppConfig."""
        app_config = AppConfig.from_env()
        api_key = app_config.semantic_scholar_api_key or None

        return cls(
            api_key=api_key,
            cache_ttl_days=app_config.semantic_scholar_cache_ttl_days,
            cache_path=(
                app_config.semantic_scholar_cache_path
                if app_config.semantic_scholar_cache_path
                else DEFAULT_CACHE_PATH
            ),
        )


@dataclass
class S2Paper:
    """Paper metadata from Semantic Scholar."""

    s2_id: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    arxiv_id: str | None
    citation_count: int

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> S2Paper:
        """Parse paper from S2 API response."""
        authors = []
        for author in data.get("authors", []) or []:
            if isinstance(author, dict):
                name = author.get("name")
                if name:
                    authors.append(name)

        external_ids = data.get("externalIds", {}) or {}
        return cls(
            s2_id=data.get("paperId", ""),
            title=data.get("title", ""),
            authors=authors,
            year=data.get("year"),
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            citation_count=data.get("citationCount", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "s2_id": self.s2_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "citation_count": self.citation_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> S2Paper:
        """Deserialize from cached dict."""
        return cls(
            s2_id=data.get("s2_id", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            citation_count=data.get("citation_count", 0),
        )


@dataclass
class CitationContext:
    """Citation context from Semantic Scholar."""

    citing_paper_id: str
    citing_paper_title: str
    citing_paper_year: int | None
    intents: list[str]
    contexts: list[str]

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> CitationContext:
        """Parse citation context from S2 API response."""
        citing_paper = data.get("citingPaper", {}) or {}
        return cls(
            citing_paper_id=citing_paper.get("paperId", ""),
            citing_paper_title=citing_paper.get("title", ""),
            citing_paper_year=citing_paper.get("year"),
            intents=data.get("intents", []) or [],
            contexts=data.get("contexts", []) or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "citing_paper_id": self.citing_paper_id,
            "citing_paper_title": self.citing_paper_title,
            "citing_paper_year": self.citing_paper_year,
            "intents": self.intents,
            "contexts": self.contexts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CitationContext:
        """Deserialize from cached dict."""
        return cls(
            citing_paper_id=data.get("citing_paper_id", ""),
            citing_paper_title=data.get("citing_paper_title", ""),
            citing_paper_year=data.get("citing_paper_year"),
            intents=data.get("intents", []),
            contexts=data.get("contexts", []),
        )


@dataclass
class S2Reference:
    """Reference (outgoing citation) from Semantic Scholar."""

    cited_paper_id: str
    cited_paper_title: str
    cited_paper_year: int | None
    intents: list[str]
    contexts: list[str]

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> S2Reference:
        """Parse reference from S2 API response."""
        cited_paper = data.get("citedPaper", {}) or {}
        return cls(
            cited_paper_id=cited_paper.get("paperId", ""),
            cited_paper_title=cited_paper.get("title", ""),
            cited_paper_year=cited_paper.get("year"),
            intents=data.get("intents", []) or [],
            contexts=data.get("contexts", []) or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "cited_paper_id": self.cited_paper_id,
            "cited_paper_title": self.cited_paper_title,
            "cited_paper_year": self.cited_paper_year,
            "intents": self.intents,
            "contexts": self.contexts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> S2Reference:
        """Deserialize from cached dict."""
        return cls(
            cited_paper_id=data.get("cited_paper_id", ""),
            cited_paper_title=data.get("cited_paper_title", ""),
            cited_paper_year=data.get("cited_paper_year"),
            intents=data.get("intents", []),
            contexts=data.get("contexts", []),
        )


class SemanticScholarClient:
    """HTTP client for Semantic Scholar API.

    Provides methods to fetch paper metadata, citation contexts,
    and references. Implements caching to reduce redundant API calls.

    Rate Limiting:
        - Unauthenticated: ~100 requests / 5 min (shared pool)
        - Authenticated: 1 request / sec (dedicated)

    We use a delay-based rate limiter:
        - Unauthenticated: 3s between calls (conservative)
        - Authenticated: 1s between calls
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    PAPER_FIELDS = "paperId,title,authors,year,externalIds,citationCount"
    CITATION_FIELDS = "paperId,title,year,intents,contexts"
    REFERENCE_FIELDS = "paperId,title,year,intents,contexts"
    _NESTED_PAPER_FIELDS = frozenset({"paperId", "title", "year"})

    def __init__(self, config: S2Config | None = None):
        """Initialize client with configuration."""
        self.config = config or S2Config.from_env()
        delay = 1.0 if self.config.api_key else 3.0
        self._rate_limiter = RateLimiter(delay_seconds=delay)
        self._cache = FileCache(
            cache_path=self.config.cache_path,
            ttl_seconds=self.config.cache_ttl_days * 24 * 60 * 60,
        )

    def _normalize_identifier(self, identifier: str) -> str:
        """Normalize identifier for API requests."""
        identifier = identifier.strip()

        # S2 paper ID is a 40-char hex string
        if len(identifier) == 40 and all(c in "0123456789abcdef" for c in identifier):
            return identifier

        # DOI starts with "10."
        if identifier.startswith("10."):
            return identifier

        # arXiv ID patterns need "ARXIV:" prefix
        if "/" in identifier and not identifier.startswith("http"):
            return f"ARXIV:{identifier}"
        if "." in identifier and identifier.split(".")[0].isdigit():
            return f"ARXIV:{identifier}"

        return identifier

    def get_cache_path(self, endpoint: str, identifier: str) -> Path:
        """Get cache file path for an API call (for testing/debugging)."""
        normalized_id = self._normalize_identifier(identifier)
        key = make_cache_key(endpoint, normalized_id)
        return self._cache.get_file_path(key, prefix=f"{endpoint}_")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API request."""
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        return headers

    def get_paper(self, identifier: str, *, use_cache: bool = True) -> S2Paper | None:
        """Get paper metadata by identifier.

        Args:
            identifier: DOI, arXiv ID, or S2 paper ID.
            use_cache: Whether to use cached results.

        Returns:
            S2Paper if found, None if not found.

        Raises:
            requests.HTTPError: On HTTP errors (except 404).
        """
        normalized_id = self._normalize_identifier(identifier)
        cache_key = make_cache_key("paper", normalized_id)

        if use_cache:
            cached = self._cache.get(cache_key, prefix="paper_")
            if cached is not None:
                paper_data = cached.get("paper")
                if paper_data is not None:
                    return S2Paper.from_dict(paper_data)
                return None

        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/paper/{normalized_id}"

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params={"fields": self.PAPER_FIELDS},
                headers=self._get_headers(),
            )
            try:
                data = response.json()
            except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
                snippet = response.text[:200].replace("\n", "\\n")
                logger.error(
                    "Semantic Scholar invalid JSON for %s (status %d): %s",
                    url,
                    response.status_code,
                    snippet,
                )
                raise
            paper = S2Paper.from_api_response(data)

            if use_cache:
                self._cache.set(cache_key, {"paper": paper.to_dict()}, prefix="paper_")

            return paper

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                if use_cache:
                    self._cache.set(cache_key, {"paper": None}, prefix="paper_")
                return None
            raise

    def get_citations(
        self,
        identifier: str,
        *,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[CitationContext]:
        """Get citation contexts for a paper.

        Returns papers that cite the given paper, with intent and context.
        """
        normalized_id = self._normalize_identifier(identifier)
        cache_key = make_cache_key("citations", normalized_id, f"limit={limit}")

        if use_cache:
            cached = self._cache.get(cache_key, prefix="citations_")
            if cached is not None:
                citations_data = cached.get("citations", [])
                return [CitationContext.from_dict(c) for c in citations_data]

        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/paper/{normalized_id}/citations"
        fields = ",".join(
            [
                f"citingPaper.{f}" if f in self._NESTED_PAPER_FIELDS else f
                for f in self.CITATION_FIELDS.split(",")
            ]
        )

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params={"fields": fields, "limit": str(limit)},
                headers=self._get_headers(),
            )
            try:
                data = response.json()
            except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
                snippet = response.text[:200].replace("\n", "\\n")
                logger.error(
                    "Semantic Scholar invalid JSON for %s (status %d): %s",
                    url,
                    response.status_code,
                    snippet,
                )
                raise

            citations = [
                CitationContext.from_api_response(item) for item in data.get("data", [])
            ]

            if use_cache:
                self._cache.set(
                    cache_key,
                    {"citations": [c.to_dict() for c in citations]},
                    prefix="citations_",
                )

            return citations

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise

    def get_references(
        self,
        identifier: str,
        *,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[S2Reference]:
        """Get references (outgoing citations) for a paper.

        Returns papers that the given paper cites.
        """
        normalized_id = self._normalize_identifier(identifier)
        cache_key = make_cache_key("references", normalized_id, f"limit={limit}")

        if use_cache:
            cached = self._cache.get(cache_key, prefix="references_")
            if cached is not None:
                refs_data = cached.get("references", [])
                return [S2Reference.from_dict(r) for r in refs_data]

        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/paper/{normalized_id}/references"
        fields = ",".join(
            [
                f"citedPaper.{f}" if f in self._NESTED_PAPER_FIELDS else f
                for f in self.REFERENCE_FIELDS.split(",")
            ]
        )

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params={"fields": fields, "limit": str(limit)},
                headers=self._get_headers(),
            )
            try:
                data = response.json()
            except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
                snippet = response.text[:200].replace("\n", "\\n")
                logger.error(
                    "Semantic Scholar invalid JSON for %s (status %d): %s",
                    url,
                    response.status_code,
                    snippet,
                )
                raise

            references = [
                S2Reference.from_api_response(item) for item in data.get("data", [])
            ]

            if use_cache:
                self._cache.set(
                    cache_key,
                    {"references": [r.to_dict() for r in references]},
                    prefix="references_",
                )

            return references

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise
