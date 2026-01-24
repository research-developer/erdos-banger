"""zbMATH Open API client for math-specific metadata.

# exempt: DEBT-095

zbMATH (https://zbmath.org/) is the Zentralblatt MATH database — the gold
standard for pure mathematics with 100+ years of coverage.

Key unique data:
- MSC codes (Mathematics Subject Classification)
- Expert math reviews (not auto-generated)
- Math-specific keywords

API Reference: https://api.zbmath.org/
"""

from __future__ import annotations

import contextlib
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
DEFAULT_CACHE_PATH = Path("literature/cache/zbmath")
DEFAULT_CACHE_TTL_DAYS = 30  # Paper metadata rarely changes


@dataclass(frozen=True)
class ZbMathConfig:
    """zbMATH client configuration."""

    mailto: str | None = None
    timeout: float = DEFAULT_HTTP_TIMEOUT
    max_retries: int = RETRY_MAX_ATTEMPTS
    cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS
    cache_path: Path = field(default=DEFAULT_CACHE_PATH)

    @classmethod
    def from_env(cls) -> ZbMathConfig:
        """Create config from environment variables via AppConfig.

        Uses centralized AppConfig for environment variable reads (DEBT-075).

        Environment variables:
            ERDOS_MAILTO: Contact email for polite API access.
            ERDOS_ZBMATH_CACHE_TTL: Cache TTL in days (default: 30).
            ERDOS_ZBMATH_CACHE_PATH: Path to cache directory (for testing).

        Returns:
            ZbMathConfig instance with values from AppConfig.
        """
        app_config = AppConfig.from_env()

        return cls(
            mailto=app_config.mailto if app_config.mailto else None,
            timeout=app_config.http_timeout,
            cache_ttl_days=app_config.zbmath_cache_ttl_days,
            cache_path=(
                app_config.zbmath_cache_path
                if app_config.zbmath_cache_path
                else DEFAULT_CACHE_PATH
            ),
        )


@dataclass
class MSCCode:
    """Mathematics Subject Classification code."""

    code: str
    text: str
    scheme: str = "msc2020"
    primary: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "code": self.code,
            "text": self.text,
            "scheme": self.scheme,
            "primary": self.primary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MSCCode:
        """Deserialize from cached dict."""
        return cls(
            code=data.get("code", ""),
            text=data.get("text", ""),
            scheme=data.get("scheme", "msc2020"),
            primary=data.get("primary", False),
        )


def _extract_title(data: dict[str, Any]) -> str:
    """Extract title from API response."""
    title_data = data.get("title", {}) or {}
    return title_data.get("title", "") if isinstance(title_data, dict) else ""


def _extract_authors(data: dict[str, Any]) -> list[str]:
    """Extract author names from API response."""
    authors: list[str] = []
    contributors = data.get("contributors", {}) or {}
    for author in contributors.get("authors", []) or []:
        if isinstance(author, dict):
            name = author.get("name")
            if name:
                authors.append(name)
    return authors


def _extract_year(data: dict[str, Any]) -> int | None:
    """Extract publication year from API response."""
    year_str = data.get("year")
    if not year_str:
        return None
    with contextlib.suppress(ValueError, TypeError):
        return int(year_str)
    return None


def _extract_links(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract DOI and arXiv ID from links in API response."""
    doi = None
    arxiv_id = None
    for link in data.get("links", []) or []:
        if isinstance(link, dict):
            link_type = link.get("type")
            identifier = link.get("identifier")
            if link_type == "doi" and identifier:
                doi = identifier
            elif link_type == "arxiv" and identifier:
                arxiv_id = identifier
    return doi, arxiv_id


def _extract_journal(data: dict[str, Any]) -> str | None:
    """Extract journal name from source in API response."""
    source = data.get("source", {}) or {}
    series_list = source.get("series", []) or []
    if series_list and isinstance(series_list, list) and len(series_list) > 0:
        first_series = series_list[0]
        if isinstance(first_series, dict):
            return first_series.get("short_title") or first_series.get("title")
    return None


def _extract_msc_codes(data: dict[str, Any]) -> list[MSCCode]:
    """Extract MSC codes from API response."""
    msc_codes: list[MSCCode] = []
    for i, msc_data in enumerate(data.get("msc", []) or []):
        if isinstance(msc_data, dict):
            code = msc_data.get("code", "")
            text = msc_data.get("text", "")
            scheme = msc_data.get("scheme", "msc2020")
            # First MSC code is typically primary
            primary = i == 0
            msc_codes.append(
                MSCCode(code=code, text=text, scheme=scheme, primary=primary)
            )
    return msc_codes


def _extract_review_excerpt(data: dict[str, Any]) -> str | None:
    """Extract review excerpt (first 500 chars) from API response."""
    for contrib in data.get("editorial_contributions", []) or []:
        if isinstance(contrib, dict) and contrib.get("contribution_type") == "review":
            text = contrib.get("text")
            if text and isinstance(text, str):
                result: str = text[:500] + "..." if len(text) > 500 else text
                return result
    return None


@dataclass
class ZbMathEntry:
    """Paper metadata from zbMATH."""

    zbl_id: str  # zbMATH identifier (e.g., "1191.11025")
    internal_id: int  # Internal numeric ID
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    arxiv_id: str | None
    journal: str | None
    msc: list[MSCCode]
    keywords: list[str]
    review_excerpt: str | None  # First ~500 chars of review
    zbmath_url: str | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ZbMathEntry:
        """Parse entry from zbMATH API response.

        Args:
            data: Raw entry dict from API (the "result" field).

        Returns:
            ZbMathEntry instance.
        """
        title = _extract_title(data)
        authors = _extract_authors(data)
        year = _extract_year(data)
        doi, arxiv_id = _extract_links(data)
        journal = _extract_journal(data)
        msc_codes = _extract_msc_codes(data)
        keywords = [k for k in (data.get("keywords", []) or []) if k is not None]
        review_excerpt = _extract_review_excerpt(data)

        return cls(
            zbl_id=data.get("identifier", ""),
            internal_id=data.get("id", 0),
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            arxiv_id=arxiv_id,
            journal=journal,
            msc=msc_codes,
            keywords=keywords,
            review_excerpt=review_excerpt,
            zbmath_url=data.get("zbmath_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for caching."""
        return {
            "zbl_id": self.zbl_id,
            "internal_id": self.internal_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "journal": self.journal,
            "msc": [msc.to_dict() for msc in self.msc],
            "keywords": self.keywords,
            "review_excerpt": self.review_excerpt,
            "zbmath_url": self.zbmath_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZbMathEntry:
        """Deserialize from cached dict."""
        msc_list = [MSCCode.from_dict(m) for m in data.get("msc", [])]
        return cls(
            zbl_id=data.get("zbl_id", ""),
            internal_id=data.get("internal_id", 0),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            journal=data.get("journal"),
            msc=msc_list,
            keywords=data.get("keywords", []),
            review_excerpt=data.get("review_excerpt"),
            zbmath_url=data.get("zbmath_url"),
        )


def msc_code_to_json(msc: MSCCode) -> dict[str, Any]:
    """Format an MSCCode for CLI JSON output (stable shape)."""
    return {
        "code": msc.code,
        "text": msc.text,
        "primary": msc.primary,
    }


def zbmath_entry_to_json(entry: ZbMathEntry) -> dict[str, Any]:
    """Format a ZbMathEntry for CLI JSON output (stable shape)."""
    return {
        "zbl_id": entry.zbl_id,
        "title": entry.title,
        "authors": entry.authors,
        "year": entry.year,
        "doi": entry.doi,
        "arxiv_id": entry.arxiv_id,
        "journal": entry.journal,
        "msc": [msc_code_to_json(m) for m in entry.msc],
        "keywords": entry.keywords,
        "review_excerpt": entry.review_excerpt,
        "zbmath_url": entry.zbmath_url,
    }


class ZbMathClient:
    """HTTP client for zbMATH Open API.

    Provides methods to fetch paper metadata and search by MSC code.
    Implements caching to reduce redundant API calls.

    Rate Limiting:
        zbMATH doesn't publish explicit rate limits, so we use
        a conservative 2-second delay between requests.
    """

    BASE_URL = "https://api.zbmath.org/v1"

    def __init__(self, config: ZbMathConfig | None = None):
        """Initialize client with configuration.

        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or ZbMathConfig.from_env()
        # Conservative rate limiting: 2s between calls
        self._rate_limiter = RateLimiter(delay_seconds=2.0)

    @property
    def rate_limit_delay_seconds(self) -> float:
        """Return the configured delay between zbMATH API calls."""
        return self._rate_limiter.delay_seconds

    def _normalize_zbl_id(self, zbl_id: str) -> str:
        """Normalize zbMATH ID.

        Args:
            zbl_id: Raw zbMATH ID (may have "Zbl " prefix, spaces, etc.)

        Returns:
            Normalized ID.
        """
        # Remove common prefixes and whitespace
        normalized = zbl_id.strip()
        if normalized.lower().startswith("zbl "):
            normalized = normalized[4:].strip()
        if normalized.lower().startswith("zbl"):
            normalized = normalized[3:].strip()
        return normalized

    def _is_identifier_format(self, zbl_id: str) -> bool:
        """Check if ID is in identifier format (e.g., '1191.11025').

        Args:
            zbl_id: Normalized zbMATH ID.

        Returns:
            True if identifier format, False if numeric internal ID.
        """
        # Identifier format contains a dot (e.g., "1191.11025")
        # Internal IDs are pure numbers (e.g., "5578697")
        return "." in zbl_id

    def _cache_key(self, endpoint: str, identifier: str) -> str:
        """Generate cache key from endpoint and identifier.

        Args:
            endpoint: API endpoint name (zbl, doi, msc, title).
            identifier: Search identifier.

        Returns:
            SHA256 hash for cache filename.
        """
        # Normalize the identifier for consistent caching
        normalized_id = self._normalize_zbl_id(identifier)
        normalized = f"{endpoint}:{normalized_id.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_cache_path(self, endpoint: str, identifier: str) -> Path:
        """Get cache file path for an API call.

        Args:
            endpoint: API endpoint name.
            identifier: Search identifier.

        Returns:
            Path to cache file.
        """
        cache_key = self._cache_key(endpoint, identifier)
        return self.config.cache_path / f"{endpoint}_{cache_key}.json"

    def _load_from_cache(self, endpoint: str, identifier: str) -> dict[str, Any] | None:
        """Load cached response if valid.

        Args:
            endpoint: API endpoint name.
            identifier: Search identifier.

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
            cached_at_raw = data.get("cached_at", 0)
            try:
                cached_at = float(cached_at_raw)
            except (TypeError, ValueError):
                logger.debug(
                    "Corrupt cache (invalid cached_at=%r) for %s:%s",
                    cached_at_raw,
                    endpoint,
                    identifier,
                )
                return None
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
            identifier: Search identifier.
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
            Headers dict with polite identification.
        """
        headers = {"Accept": "application/json"}
        if self.config.mailto:
            headers["User-Agent"] = f"erdos-banger/1.0 (mailto:{self.config.mailto})"
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

    def get_by_zbl_id(
        self, zbl_id: str, *, use_cache: bool = True
    ) -> ZbMathEntry | None:
        """Get entry by zbMATH ID.

        Args:
            zbl_id: zbMATH ID (e.g., "5578697" or "1191.11025").
            use_cache: Whether to use cached results.

        Returns:
            ZbMathEntry if found, None if not found.

        Raises:
            requests.HTTPError: On HTTP errors (except 404).
        """
        normalized_id = self._normalize_zbl_id(zbl_id)

        # Check cache first
        if use_cache:
            cached = self._load_from_cache("zbl", normalized_id)
            if cached is not None:
                entry_data = cached.get("entry")
                if entry_data is not None:
                    return ZbMathEntry.from_dict(entry_data)
                return None

        # For identifier format (e.g., "1191.11025"), use search endpoint
        if self._is_identifier_format(normalized_id):
            return self._search_by_identifier(normalized_id, use_cache)

        # For numeric IDs, use direct lookup
        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/{normalized_id}"

        try:
            response = self._get_with_retry(url, {})
            data = response.json()

            result = data.get("result")
            if result is None:
                # Cache the "not found" result
                if use_cache:
                    self._save_to_cache("zbl", normalized_id, {"entry": None})
                return None

            entry = ZbMathEntry.from_api_response(result)

            # Cache result
            if use_cache:
                self._save_to_cache("zbl", normalized_id, {"entry": entry.to_dict()})

            return entry

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # Cache the "not found" result
                if use_cache:
                    self._save_to_cache("zbl", normalized_id, {"entry": None})
                return None
            raise

    def _search_by_identifier(
        self, identifier: str, use_cache: bool
    ) -> ZbMathEntry | None:
        """Search for entry by zbMATH identifier (e.g., '1191.11025').

        Args:
            identifier: zbMATH identifier.
            use_cache: Whether to cache the result.

        Returns:
            ZbMathEntry if found, None otherwise.
        """
        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/_search"
        params = {"search_string": f"an:{identifier}", "results_per_page": 1}

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            results = data.get("result", [])
            if not results:
                if use_cache:
                    self._save_to_cache("zbl", identifier, {"entry": None})
                return None

            entry = ZbMathEntry.from_api_response(results[0])

            if use_cache:
                self._save_to_cache("zbl", identifier, {"entry": entry.to_dict()})

            return entry

        except requests.HTTPError:
            raise

    def get_by_doi(self, doi: str, *, use_cache: bool = True) -> ZbMathEntry | None:
        """Get entry by DOI.

        Args:
            doi: DOI string (e.g., "10.4007/annals.2008.167.481").
            use_cache: Whether to use cached results.

        Returns:
            ZbMathEntry if found, None if not found.

        Raises:
            requests.HTTPError: On HTTP errors.
        """
        # Check cache first
        if use_cache:
            cached = self._load_from_cache("doi", doi)
            if cached is not None:
                entry_data = cached.get("entry")
                if entry_data is not None:
                    return ZbMathEntry.from_dict(entry_data)
                return None

        # Search by DOI
        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/_search"
        params = {"search_string": f"doi:{doi}", "results_per_page": 1}

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            results = data.get("result", [])
            if not results:
                if use_cache:
                    self._save_to_cache("doi", doi, {"entry": None})
                return None

            entry = ZbMathEntry.from_api_response(results[0])

            if use_cache:
                self._save_to_cache("doi", doi, {"entry": entry.to_dict()})

            return entry

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                # Cache the "not found" result
                if use_cache:
                    self._save_to_cache("doi", doi, {"entry": None})
                return None
            raise

    def search_by_msc(
        self,
        msc_code: str,
        *,
        limit: int = 20,
        year_min: int | None = None,
        year_max: int | None = None,
        use_cache: bool = True,
    ) -> list[ZbMathEntry]:
        """Search by MSC (Mathematics Subject Classification) code.

        Args:
            msc_code: MSC code (e.g., "11B05").
            limit: Maximum number of results.
            year_min: Minimum publication year.
            year_max: Maximum publication year.
            use_cache: Whether to use cached results.

        Returns:
            List of ZbMathEntry objects.

        Raises:
            requests.HTTPError: On HTTP errors.
        """
        cache_key = f"{msc_code}:limit={limit}:years={year_min}-{year_max}"

        # Check cache first
        if use_cache:
            cached = self._load_from_cache("msc", cache_key)
            if cached is not None:
                entries_data = cached.get("entries", [])
                return [ZbMathEntry.from_dict(e) for e in entries_data]

        # Build search query
        query_parts = [f"cc:{msc_code}"]
        if year_min is not None or year_max is not None:
            year_range = f"{year_min or ''}-{year_max or ''}"
            query_parts.append(f"py:{year_range}")

        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/_search"
        params = {
            "search_string": " ".join(query_parts),
            "results_per_page": limit,
        }

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            results = data.get("result", []) or []
            entries = [ZbMathEntry.from_api_response(r) for r in results]

            if use_cache:
                self._save_to_cache(
                    "msc", cache_key, {"entries": [e.to_dict() for e in entries]}
                )

            return entries

        except requests.HTTPError:
            raise

    def search_by_title(
        self, title: str, *, limit: int = 10, use_cache: bool = True
    ) -> list[ZbMathEntry]:
        """Search by title keywords.

        Args:
            title: Title keywords to search for.
            limit: Maximum number of results.
            use_cache: Whether to use cached results.

        Returns:
            List of ZbMathEntry objects.

        Raises:
            requests.HTTPError: On HTTP errors.
        """
        cache_key = f"{title}:limit={limit}"

        # Check cache first
        if use_cache:
            cached = self._load_from_cache("title", cache_key)
            if cached is not None:
                entries_data = cached.get("entries", [])
                return [ZbMathEntry.from_dict(e) for e in entries_data]

        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/_search"
        # Use ti: prefix for title search
        params = {"search_string": f"ti:{title}", "results_per_page": limit}

        try:
            response = self._get_with_retry(url, params)
            data = response.json()

            results = data.get("result", []) or []
            entries = [ZbMathEntry.from_api_response(r) for r in results]

            if use_cache:
                self._save_to_cache(
                    "title", cache_key, {"entries": [e.to_dict() for e in entries]}
                )

            return entries

        except requests.HTTPError:
            raise
