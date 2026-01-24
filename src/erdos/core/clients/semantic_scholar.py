"""Semantic Scholar API client for citation context extraction.

# exempt: DEBT-094

Semantic Scholar (https://www.semanticscholar.org/) provides citation intent
classification and in-context snippets - information not available in other APIs.

API Reference: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from erdos.core.config import AppConfig
from erdos.core.constants import (
    DEFAULT_HTTP_TIMEOUT,
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
)
from erdos.core.rate_limiter import RateLimiter


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
        """Create config from environment variables via AppConfig.

        Uses centralized AppConfig for environment variable reads (DEBT-075).

        Returns:
            S2Config instance with values from AppConfig.
        """
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
        """Parse paper from S2 API response.

        Args:
            data: Raw paper dict from API.

        Returns:
            S2Paper instance.
        """
        authors = []
        for author in data.get("authors", []) or []:
            if isinstance(author, dict):
                name = author.get("name")
                if name:
                    authors.append(name)

        # Extract arXiv ID from externalIds
        external_ids = data.get("externalIds", {}) or {}
        arxiv_id = external_ids.get("ArXiv")
        doi = external_ids.get("DOI")

        return cls(
            s2_id=data.get("paperId", ""),
            title=data.get("title", ""),
            authors=authors,
            year=data.get("year"),
            doi=doi,
            arxiv_id=arxiv_id,
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
    intents: list[str]  # background, methodology, result
    contexts: list[str]  # Actual text snippets

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> CitationContext:
        """Parse citation context from S2 API response.

        Args:
            data: Raw citation dict from API.

        Returns:
            CitationContext instance.
        """
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
        """Parse reference from S2 API response.

        Args:
            data: Raw reference dict from API.

        Returns:
            S2Reference instance.
        """
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

    # Paper fields to request from the API
    PAPER_FIELDS = "paperId,title,authors,year,externalIds,citationCount"
    CITATION_FIELDS = "paperId,title,year,intents,contexts"
    REFERENCE_FIELDS = "paperId,title,year,intents,contexts"

    def __init__(self, config: S2Config | None = None):
        """Initialize client with configuration.

        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or S2Config.from_env()
        # Conservative rate limiting:
        # - unauthenticated: 3s between calls
        # - authenticated: 1s between calls
        delay = 1.0 if self.config.api_key else 3.0
        self._rate_limiter = RateLimiter(delay_seconds=delay)

    def _normalize_identifier(self, identifier: str) -> str:
        """Normalize identifier for API requests.

        The S2 API accepts various identifier formats:
        - DOI: "10.xxxx/..." → send as-is
        - arXiv ID: "math/0404188" or "2301.00001" → prefix with "ARXIV:"
        - S2 Paper ID: 40-char hex string → send as-is

        Args:
            identifier: DOI, arXiv ID, or S2 paper ID.

        Returns:
            Normalized identifier for API.
        """
        identifier = identifier.strip()

        # S2 paper ID is a 40-char hex string
        if len(identifier) == 40 and all(c in "0123456789abcdef" for c in identifier):
            return identifier

        # DOI starts with "10."
        if identifier.startswith("10."):
            return identifier

        # arXiv ID patterns: "math/0404188", "2301.00001", etc.
        # Need to prefix with "ARXIV:" for the API
        if "/" in identifier and not identifier.startswith("http"):
            # Legacy format: math/0404188
            return f"ARXIV:{identifier}"
        if "." in identifier and identifier.split(".")[0].isdigit():
            # Modern format: 2301.00001
            return f"ARXIV:{identifier}"

        # Assume it's an S2 ID or DOI
        return identifier

    def _cache_key(self, endpoint: str, identifier: str) -> str:
        """Generate cache key from endpoint and identifier.

        Args:
            endpoint: API endpoint name (paper, citations, references).
            identifier: Paper identifier.

        Returns:
            SHA256 hash for cache filename.
        """
        normalized = f"{endpoint}:{identifier.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_cache_path(self, endpoint: str, identifier: str) -> Path:
        """Get cache file path for an API call.

        Args:
            endpoint: API endpoint name.
            identifier: Paper identifier.

        Returns:
            Path to cache file.
        """
        cache_key = self._cache_key(endpoint, identifier)
        return self.config.cache_path / f"{endpoint}_{cache_key}.json"

    def _load_from_cache(self, endpoint: str, identifier: str) -> dict[str, Any] | None:
        """Load cached response if valid.

        Args:
            endpoint: API endpoint name.
            identifier: Paper identifier.

        Returns:
            Cached data if valid and not expired, None otherwise.
        """
        cache_file = self.get_cache_path(endpoint, identifier)
        if not cache_file.exists():
            return None

        try:
            with cache_file.open() as f:
                data: dict[str, Any] = json.load(f)

            # Check TTL
            cached_at = data.get("cached_at", 0)
            ttl_seconds = self.config.cache_ttl_days * 24 * 60 * 60
            if time.time() - cached_at > ttl_seconds:
                logger.debug("Cache expired for %s:%s", endpoint, identifier)
                return None

            logger.debug("Cache hit for %s:%s", endpoint, identifier)
            return data

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load cache for %s:%s: %s", endpoint, identifier, e
            )
            return None

    def _save_to_cache(
        self, endpoint: str, identifier: str, data: dict[str, Any]
    ) -> None:
        """Save response to cache.

        Args:
            endpoint: API endpoint name.
            identifier: Paper identifier.
            data: Data to cache.
        """
        cache_file = self.get_cache_path(endpoint, identifier)

        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {**data, "cached_at": time.time()}

            with cache_file.open("w") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug("Cached response for %s:%s", endpoint, identifier)

        except OSError as e:
            logger.warning(
                "Failed to cache response for %s:%s: %s", endpoint, identifier, e
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API request.

        Returns:
            Headers dict with optional API key.
        """
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        return headers

    def _get_with_retry(self, url: str, params: dict[str, Any]) -> requests.Response:
        """GET with retry logic for transient failures.

        Args:
            url: API endpoint URL.
            params: Query parameters.

        Returns:
            requests.Response on success.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
            requests.Timeout: After all retries exhausted.
        """
        last_error: Exception | None = None
        last_response: requests.Response | None = None

        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=self.config.timeout,
                )

                if response.status_code in RETRYABLE_STATUS_CODES:
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
        # Check Retry-After header for 429
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), RETRY_MAX_DELAY)
                except ValueError:
                    pass

        # Exponential backoff: base_delay * 2^attempt
        delay = RETRY_BASE_DELAY * (2**attempt)
        return float(min(delay, RETRY_MAX_DELAY))

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
        # Check cache first
        if use_cache:
            cached = self._load_from_cache("paper", identifier)
            if cached is not None:
                paper_data = cached.get("paper")
                if paper_data is not None:
                    return S2Paper.from_dict(paper_data)
                return None

        # Make API request
        self._rate_limiter.sleep_if_needed()

        normalized_id = self._normalize_identifier(identifier)
        url = f"{self.BASE_URL}/paper/{normalized_id}"
        params = {"fields": self.PAPER_FIELDS}

        try:
            response = self._get_with_retry(url, params)
            data = response.json()
            paper = S2Paper.from_api_response(data)

            # Cache result
            if use_cache:
                self._save_to_cache("paper", identifier, {"paper": paper.to_dict()})

            return paper

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # Cache the "not found" result too
                if use_cache:
                    self._save_to_cache("paper", identifier, {"paper": None})
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

        Args:
            identifier: DOI, arXiv ID, or S2 paper ID.
            limit: Maximum number of citations to return.
            use_cache: Whether to use cached results.

        Returns:
            List of CitationContext objects.

        Raises:
            requests.HTTPError: On HTTP errors.
        """
        cache_key = f"{identifier}:limit={limit}"

        # Check cache first
        if use_cache:
            cached = self._load_from_cache("citations", cache_key)
            if cached is not None:
                citations_data = cached.get("citations", [])
                return [CitationContext.from_dict(c) for c in citations_data]

        # Make API request
        self._rate_limiter.sleep_if_needed()

        normalized_id = self._normalize_identifier(identifier)
        url = f"{self.BASE_URL}/paper/{normalized_id}/citations"
        params = {
            "fields": f"citingPaper.{self.CITATION_FIELDS}",
            "limit": limit,
        }

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            citations = [
                CitationContext.from_api_response(item) for item in data.get("data", [])
            ]

            # Cache result
            if use_cache:
                self._save_to_cache(
                    "citations",
                    cache_key,
                    {"citations": [c.to_dict() for c in citations]},
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

        Args:
            identifier: DOI, arXiv ID, or S2 paper ID.
            limit: Maximum number of references to return.
            use_cache: Whether to use cached results.

        Returns:
            List of S2Reference objects.

        Raises:
            requests.HTTPError: On HTTP errors.
        """
        cache_key = f"{identifier}:limit={limit}"

        # Check cache first
        if use_cache:
            cached = self._load_from_cache("references", cache_key)
            if cached is not None:
                refs_data = cached.get("references", [])
                return [S2Reference.from_dict(r) for r in refs_data]

        # Make API request
        self._rate_limiter.sleep_if_needed()

        normalized_id = self._normalize_identifier(identifier)
        url = f"{self.BASE_URL}/paper/{normalized_id}/references"
        params = {
            "fields": f"citedPaper.{self.REFERENCE_FIELDS}",
            "limit": limit,
        }

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            references = [
                S2Reference.from_api_response(item) for item in data.get("data", [])
            ]

            # Cache result
            if use_cache:
                self._save_to_cache(
                    "references",
                    cache_key,
                    {"references": [r.to_dict() for r in references]},
                )

            return references

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return []
            raise
