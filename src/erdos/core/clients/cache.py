"""Shared file-based cache for HTTP API clients.

Provides a generic FileCache class that handles:
- SHA256 key generation from request parameters
- TTL-based expiry with robust timestamp validation
- JSON serialization with error handling
- Configurable cache path and TTL

This module consolidates caching logic that was previously duplicated
across exa.py, semantic_scholar.py, and zbmath.py (DEBT-093).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class FileCache:
    """Generic file-based JSON cache with TTL expiry.

    Stores cached responses as JSON files, keyed by SHA256 hash of the
    cache key string. Supports TTL-based expiry with robust validation.

    Example:
        cache = FileCache(
            cache_path=Path("literature/cache/api"),
            ttl_seconds=24 * 60 * 60,  # 24 hours
        )

        # Check cache
        data = cache.get("search:query=foo|limit=10")
        if data is None:
            # Fetch from API...
            cache.set("search:query=foo|limit=10", response_data)
    """

    def __init__(self, cache_path: Path, ttl_seconds: float) -> None:
        """Initialize cache with storage path and TTL.

        Args:
            cache_path: Directory to store cache files.
            ttl_seconds: Time-to-live in seconds (0 = no expiry).
        """
        self.cache_path = cache_path
        self.ttl_seconds = ttl_seconds

    def _hash_key(self, key: str) -> str:
        """Generate SHA256 hash of cache key.

        Args:
            key: Cache key string (should be normalized by caller).

        Returns:
            40-character hex digest.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def get_file_path(self, key: str, *, prefix: str = "") -> Path:
        """Get file path for a cache key.

        Args:
            key: Cache key string.
            prefix: Optional prefix for the filename (e.g., "paper_").

        Returns:
            Path to the cache file.
        """
        hashed = self._hash_key(key)
        filename = f"{prefix}{hashed}.json" if prefix else f"{hashed}.json"
        return self.cache_path / filename

    def get(self, key: str, *, prefix: str = "") -> dict[str, Any] | None:
        """Load data from cache if valid and not expired.

        Args:
            key: Cache key string.
            prefix: Optional filename prefix.

        Returns:
            Cached data dict if valid, None if missing/expired/corrupt.
        """
        cache_file = self.get_file_path(key, prefix=prefix)
        if not cache_file.exists():
            return None

        try:
            with cache_file.open() as f:
                data: dict[str, Any] = json.load(f)

            # Validate and check TTL
            cached_at_raw = data.get("_cached_at", 0)
            try:
                cached_at = float(cached_at_raw)
            except (TypeError, ValueError):
                logger.debug(
                    "Corrupt cache (invalid _cached_at=%r) for key: %s",
                    cached_at_raw,
                    key[:50],
                )
                return None

            if self.ttl_seconds > 0 and time.time() - cached_at > self.ttl_seconds:
                logger.debug("Cache expired for key: %s", key[:50])
                return None

            logger.debug("Cache hit for key: %s", key[:50])
            return data

        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cache for key %s: %s", key[:50], e)
            return None

    def set(self, key: str, data: dict[str, Any], *, prefix: str = "") -> None:
        """Save data to cache.

        Args:
            key: Cache key string.
            data: Data dict to cache (will be shallow-copied, _cached_at added).
            prefix: Optional filename prefix.
        """
        cache_file = self.get_file_path(key, prefix=prefix)

        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {**data, "_cached_at": time.time()}

            with cache_file.open("w") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug("Cached data for key: %s", key[:50])

        except OSError as e:
            logger.warning("Failed to cache data for key %s: %s", key[:50], e)


def make_cache_key(*parts: str | int | float | None) -> str:
    """Build a normalized cache key from parts.

    Args:
        *parts: Key components (None values are converted to empty string).

    Returns:
        Normalized cache key string with parts joined by "|".

    Example:
        >>> make_cache_key("search", "query=foo", "limit=10")
        'search|query=foo|limit=10'
        >>> make_cache_key("paper", None, "arxiv:2301.00001")
        'paper||arxiv:2301.00001'
    """
    normalized = [str(p).lower().strip() if p is not None else "" for p in parts]
    return "|".join(normalized)
