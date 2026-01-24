"""OpenAlex API client for academic metadata.

OpenAlex (https://openalex.org/) is a fully open catalog of scholarly works
with 271M+ works. This client provides access to work metadata using the
OpenAlex REST API.

API Reference: https://docs.openalex.org/
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import requests

from erdos.core.clients.openalex_transform import openalex_to_reference
from erdos.core.config import AppConfig
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


@dataclass(frozen=True)
class OpenAlexConfig:
    """OpenAlex client configuration."""

    email: str | None = None
    api_key: str | None = None
    timeout: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> OpenAlexConfig:
        """Create config from environment variables.

        Uses :class:`erdos.core.config.AppConfig` as the SSOT for environment reads.
        """
        config = AppConfig.from_env()
        return cls(
            email=config.mailto,
            api_key=config.openalex_api_key or None,
        )


class OpenAlexClient:
    """Client for OpenAlex API.

    Provides methods to fetch academic metadata by DOI, arXiv ID,
    or search query. Uses retry logic for transient failures.
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(self, config: OpenAlexConfig | None = None):
        """Initialize client with configuration.

        Args:
            config: Client configuration. If None, loads from environment.
        """
        self.config = config or OpenAlexConfig.from_env()

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        """Build request parameters with optional mailto and api_key."""
        params = dict(kwargs)
        if self.config.email:
            params["mailto"] = self.config.email
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        return params

    def _fetch(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch JSON from OpenAlex API with retry.

        Args:
            url: API endpoint URL.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            requests.HTTPError: On non-retryable HTTP errors.
            requests.Timeout: After all retries exhausted.
            json.JSONDecodeError: If response is not valid JSON.
        """
        logger.debug("Fetching OpenAlex: %s", url)
        start_time = time.monotonic()

        response = fetch_with_retry(
            url,
            timeout=self.config.timeout,
            max_attempts=self.config.max_retries,
            params=params,
        )
        elapsed = time.monotonic() - start_time
        logger.debug(
            "OpenAlex response: %d bytes in %.2fs (status %d)",
            len(response.content),
            elapsed,
            response.status_code,
        )

        try:
            return response.json()  # type: ignore[no-any-return]
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
            snippet = response.text[:200].replace("\n", "\\n")
            logger.error(
                "OpenAlex invalid JSON for %s (status %d): %s",
                url,
                response.status_code,
                snippet,
            )
            raise

    def get_by_doi(self, doi: str) -> ReferenceRecord:
        """Fetch work by DOI.

        Args:
            doi: DOI without prefix (e.g., "10.1038/nature12373").

        Returns:
            ReferenceRecord with work metadata.

        Raises:
            requests.HTTPError: If work not found (404) or other HTTP error.
        """
        # Encode DOI for URL, keeping "/" unencoded (per OpenAlex API format)
        encoded_doi = quote(doi, safe="/")
        url = f"{self.BASE_URL}/works/https://doi.org/{encoded_doi}"
        params = self._params()

        work = self._fetch(url, params)
        return openalex_to_reference(work)

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord:
        """Fetch work by arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g., "2301.00001").

        Returns:
            ReferenceRecord with work metadata.

        Raises:
            ValueError: If no work found for the arXiv ID.
        """
        arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)
        doi = f"10.48550/arxiv.{arxiv_id_clean}"

        try:
            ref = self.get_by_doi(doi)
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            # Fast-path DOI lookup is not always supported by OpenAlex even when the work
            # exists (some works have a different canonical DOI and only expose the arXiv
            # DOI/landing page via locations[*].landing_page_url). Fall back to a locations
            # filter query when the DOI lookup returns 404.
            if response is None or response.status_code != 404:
                raise
            url = f"{self.BASE_URL}/works"
            landing_candidates = [
                f"https://doi.org/{doi}",
                f"http://arxiv.org/abs/{arxiv_id_clean}",
                f"https://arxiv.org/abs/{arxiv_id_clean}",
            ]
            for landing in landing_candidates:
                params = self._params(
                    filter=f"locations.landing_page_url:{landing}",
                    per_page=1,
                )
                payload = self._fetch(url, params)
                results = payload.get("results", [])
                if isinstance(results, list) and results:
                    ref = openalex_to_reference(results[0])
                    break
            else:
                raise ValueError(f"No work found for arXiv:{arxiv_id_clean}") from e

        # Ensure the arXiv ID is populated consistently.
        ref.arxiv_id = arxiv_id_clean
        return ref

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract.

        Args:
            query: Search query string.
            limit: Maximum results to return.

        Returns:
            List of matching ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(search=query, per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]

    def get_citations(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Get works that cite this work.

        Args:
            work_id: OpenAlex work ID (e.g., "https://openalex.org/W2741809807").
            limit: Maximum results to return.

        Returns:
            List of citing ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"cites:{work_id}", per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]

    def get_references(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Get works cited by this work.

        Args:
            work_id: OpenAlex work ID (e.g., "https://openalex.org/W2741809807").
            limit: Maximum results to return.

        Returns:
            List of referenced ReferenceRecords.
        """
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"cited_by:{work_id}", per_page=limit)

        response = self._fetch(url, params)
        results = response.get("results", [])

        return [openalex_to_reference(work) for work in results]
