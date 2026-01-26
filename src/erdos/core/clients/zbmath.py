"""zbMATH Open API client for math-specific metadata.

zbMATH (https://zbmath.org/) is the Zentralblatt MATH database — the gold
standard for pure mathematics with 100+ years of coverage.

Key unique data:
- MSC codes (Mathematics Subject Classification)
- Expert math reviews (not auto-generated)
- Math-specific keywords

API Reference: https://api.zbmath.org/

# exempt: DEBT-093 — 627 LOC is 127 over threshold. Justified per DEBT-093
# resolution: zbMATH has the most complex API response structure (nested
# contributors, editorial_contributions, MSC codes). All duplicated
# infrastructure was extracted to shared modules.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import requests

from erdos.core.clients.cache import FileCache, make_cache_key
from erdos.core.config import AppConfig
from erdos.core.constants import DEFAULT_HTTP_TIMEOUT, RETRY_MAX_ATTEMPTS
from erdos.core.rate_limiter import RateLimiter
from erdos.core.retry import fetch_with_retry


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
        """Create config from environment variables via AppConfig."""
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


# --- Response extraction helpers ---


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
            msc_codes.append(
                MSCCode(
                    code=msc_data.get("code", ""),
                    text=msc_data.get("text", ""),
                    scheme=msc_data.get("scheme", "msc2020"),
                    primary=i == 0,  # First MSC code is typically primary
                )
            )
    return msc_codes


def _extract_review_excerpt(data: dict[str, Any]) -> str | None:
    """Extract review excerpt (first 500 chars) from API response."""
    for contrib in data.get("editorial_contributions", []) or []:
        if isinstance(contrib, dict) and contrib.get("contribution_type") == "review":
            text = contrib.get("text")
            if isinstance(text, str) and text:
                excerpt: str = text[:500] + "..." if len(text) > 500 else text
                return excerpt
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
        """Parse entry from zbMATH API response."""
        doi, arxiv_id = _extract_links(data)
        return cls(
            zbl_id=data.get("identifier", ""),
            internal_id=data.get("id", 0),
            title=_extract_title(data),
            authors=_extract_authors(data),
            year=_extract_year(data),
            doi=doi,
            arxiv_id=arxiv_id,
            journal=_extract_journal(data),
            msc=_extract_msc_codes(data),
            keywords=[k for k in (data.get("keywords", []) or []) if k is not None],
            review_excerpt=_extract_review_excerpt(data),
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
        return cls(
            zbl_id=data.get("zbl_id", ""),
            internal_id=data.get("internal_id", 0),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            doi=data.get("doi"),
            arxiv_id=data.get("arxiv_id"),
            journal=data.get("journal"),
            msc=[MSCCode.from_dict(m) for m in data.get("msc", [])],
            keywords=data.get("keywords", []),
            review_excerpt=data.get("review_excerpt"),
            zbmath_url=data.get("zbmath_url"),
        )


def msc_code_to_json(msc: MSCCode) -> dict[str, Any]:
    """Format an MSCCode for CLI JSON output (stable shape)."""
    return {"code": msc.code, "text": msc.text, "primary": msc.primary}


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
    _CACHE_MISS = object()

    def __init__(self, config: ZbMathConfig | None = None):
        """Initialize client with configuration."""
        self.config = config or ZbMathConfig.from_env()
        self._rate_limiter = RateLimiter(delay_seconds=2.0)
        self._cache = FileCache(
            cache_path=self.config.cache_path,
            ttl_seconds=self.config.cache_ttl_days * 24 * 60 * 60,
        )

    @property
    def rate_limit_delay_seconds(self) -> float:
        """Return the configured delay between zbMATH API calls."""
        return self._rate_limiter.delay_seconds

    def _normalize_zbl_id(self, zbl_id: str) -> str:
        """Normalize zbMATH ID."""
        normalized = zbl_id.strip()
        if normalized.lower().startswith("zbl "):
            normalized = normalized[4:].strip()
        if normalized.lower().startswith("zbl"):
            normalized = normalized[3:].strip()
        return normalized

    def _is_identifier_format(self, zbl_id: str) -> bool:
        """Check if ID is in identifier format (e.g., '1191.11025')."""
        return "." in zbl_id

    def get_cache_path(self, endpoint: str, identifier: str) -> Path:
        """Get cache file path for an API call (for testing/debugging)."""
        normalized_id = self._normalize_zbl_id(identifier)
        key = make_cache_key(endpoint, normalized_id)
        return self._cache.get_file_path(key, prefix=f"{endpoint}_")

    def _get_cached_zbl_entry(
        self, cache_key: str, *, use_cache: bool
    ) -> ZbMathEntry | None | object:
        """Return a cached entry, None (cached miss), or sentinel (cache disabled/miss)."""
        if not use_cache:
            return self._CACHE_MISS
        cached = self._cache.get(cache_key, prefix="zbl_")
        if cached is None:
            return self._CACHE_MISS
        entry_data = cached.get("entry")
        if entry_data is None:
            return None
        return ZbMathEntry.from_dict(entry_data)

    def _cache_zbl_entry(
        self, cache_key: str, entry: ZbMathEntry | None, *, use_cache: bool
    ) -> None:
        """Cache a lookup result (best-effort), including negative caching."""
        if not use_cache:
            return
        self._cache.set(
            cache_key,
            {"entry": entry.to_dict() if entry is not None else None},
            prefix="zbl_",
        )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API request."""
        headers = {"Accept": "application/json"}
        if self.config.mailto:
            headers["User-Agent"] = f"erdos-banger/1.0 (mailto:{self.config.mailto})"
        return headers

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
        cache_key = make_cache_key("zbl", normalized_id)

        cached_entry = self._get_cached_zbl_entry(cache_key, use_cache=use_cache)
        if cached_entry is not self._CACHE_MISS:
            return cast("ZbMathEntry | None", cached_entry)

        # For identifier format (e.g., "1191.11025"), use search endpoint
        if self._is_identifier_format(normalized_id):
            return self._search_by_identifier(
                normalized_id,
                cache_key=cache_key,
                use_cache=use_cache,
            )

        # For numeric IDs, use direct lookup
        self._rate_limiter.sleep_if_needed()
        url = f"{self.BASE_URL}/document/{normalized_id}"

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                headers=self._get_headers(),
            )
            data = response.json()

            result = data.get("result")
            if result is None:
                self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
                return None

            entry = ZbMathEntry.from_api_response(result)
            self._cache_zbl_entry(cache_key, entry, use_cache=use_cache)

            return entry

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
                return None
            raise

    def _search_by_identifier(
        self, identifier: str, *, cache_key: str, use_cache: bool
    ) -> ZbMathEntry | None:
        """Search for entry by zbMATH identifier (e.g., '1191.11025')."""
        self._rate_limiter.sleep_if_needed()

        url = f"{self.BASE_URL}/document/_search"
        params = {"search_string": f"an:{identifier}", "results_per_page": "1"}

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params=params,
                headers=self._get_headers(),
            )
            data = response.json()

            results = data.get("result", [])
            if not results:
                self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
                return None

            entry = ZbMathEntry.from_api_response(results[0])
            self._cache_zbl_entry(cache_key, entry, use_cache=use_cache)

            return entry

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
                return None
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
        cache_key = make_cache_key("doi", doi)

        if use_cache:
            cached = self._cache.get(cache_key, prefix="doi_")
            if cached is not None:
                entry_data = cached.get("entry")
                if entry_data is not None:
                    return ZbMathEntry.from_dict(entry_data)
                return None

        self._rate_limiter.sleep_if_needed()
        url = f"{self.BASE_URL}/document/_search"
        params = {"search_string": f"doi:{doi}", "results_per_page": "1"}

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params=params,
                headers=self._get_headers(),
            )
            data = response.json()

            results = data.get("result", [])
            if not results:
                if use_cache:
                    self._cache.set(cache_key, {"entry": None}, prefix="doi_")
                return None

            entry = ZbMathEntry.from_api_response(results[0])
            if use_cache:
                self._cache.set(cache_key, {"entry": entry.to_dict()}, prefix="doi_")

            return entry

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                if use_cache:
                    self._cache.set(cache_key, {"entry": None}, prefix="doi_")
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
        cache_key = make_cache_key(
            "msc", msc_code, f"limit={limit}", f"years={year_min}-{year_max}"
        )

        if use_cache:
            cached = self._cache.get(cache_key, prefix="msc_")
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
            "results_per_page": str(limit),
        }

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params=params,
                headers=self._get_headers(),
            )
            data = response.json()

            results = data.get("result", []) or []
            entries = [ZbMathEntry.from_api_response(r) for r in results]

            if use_cache:
                self._cache.set(
                    cache_key,
                    {"entries": [e.to_dict() for e in entries]},
                    prefix="msc_",
                )

            return entries

        except requests.HTTPError as e:
            # 404 for search means no results found (invalid MSC code, etc.)
            if e.response is not None and e.response.status_code == 404:
                if use_cache:
                    self._cache.set(cache_key, {"entries": []}, prefix="msc_")
                return []
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
        cache_key = make_cache_key("title", title, f"limit={limit}")

        if use_cache:
            cached = self._cache.get(cache_key, prefix="title_")
            if cached is not None:
                entries_data = cached.get("entries", [])
                return [ZbMathEntry.from_dict(e) for e in entries_data]

        self._rate_limiter.sleep_if_needed()
        url = f"{self.BASE_URL}/document/_search"
        params = {"search_string": f"ti:{title}", "results_per_page": str(limit)}

        try:
            response = fetch_with_retry(
                url,
                timeout=self.config.timeout,
                max_attempts=self.config.max_retries,
                params=params,
                headers=self._get_headers(),
            )
            data = response.json()

            results = data.get("result", []) or []
            entries = [ZbMathEntry.from_api_response(r) for r in results]

            if use_cache:
                self._cache.set(
                    cache_key,
                    {"entries": [e.to_dict() for e in entries]},
                    prefix="title_",
                )

            return entries

        except requests.HTTPError as e:
            # 404 for search means no results found
            if e.response is not None and e.response.status_code == 404:
                if use_cache:
                    self._cache.set(cache_key, {"entries": []}, prefix="title_")
                return []
            raise
