"""OpenAlex API client for academic metadata.

OpenAlex (https://openalex.org/) is a fully open catalog of scholarly works
with 271M+ works. This client provides access to work metadata using the
OpenAlex REST API.

API Reference: https://docs.openalex.org/
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from erdos.core.models import OpenAccessStatus, ReferenceRecord
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenAlexConfig:
    """OpenAlex client configuration."""

    email: str | None = None
    timeout: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> OpenAlexConfig:
        """Create config from environment variables.

        Checks ERDOS_MAILTO first, then OPENALEX_EMAIL.
        """
        return cls(
            email=os.getenv("ERDOS_MAILTO") or os.getenv("OPENALEX_EMAIL"),
        )


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Convert OpenAlex inverted index to plain text abstract.

    OpenAlex stores abstracts as inverted indexes where each word maps to
    its positions in the text. This function reconstructs the original text.

    Args:
        inverted_index: Word -> positions mapping from OpenAlex.

    Returns:
        Plain text abstract or None if input is empty/None.
    """
    if not inverted_index:
        return None

    # Build (position, word) pairs
    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))

    # Sort by position and join
    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


def extract_arxiv_id(ids: dict[str, Any]) -> str | None:
    """Extract arXiv ID from OpenAlex IDs object.

    Args:
        ids: OpenAlex IDs object containing various identifiers.

    Returns:
        arXiv ID (e.g., "2301.00001" or "math/0703001") or None if not present.
    """
    arxiv_url: str | None = ids.get("arxiv")
    if arxiv_url:
        # Format: https://arxiv.org/abs/2301.00001 or https://arxiv.org/abs/math/0703001
        # Remove the base URL prefix to get the ID
        prefix = "https://arxiv.org/abs/"
        if arxiv_url.startswith(prefix):
            return arxiv_url[len(prefix) :]
        # Fallback: take everything after the last "abs/"
        if "/abs/" in arxiv_url:
            return arxiv_url.split("/abs/")[-1]
        return arxiv_url.split("/")[-1]
    return None


def find_pdf_url(work: dict[str, Any]) -> str | None:
    """Find best PDF URL from OpenAlex work locations.

    Checks primary location first, then alternate locations.

    Args:
        work: OpenAlex work object.

    Returns:
        PDF URL or None if not available.
    """
    # Check primary location first
    primary: dict[str, Any] = work.get("primary_location", {}) or {}
    pdf_url: str | None = primary.get("pdf_url")
    if pdf_url:
        return pdf_url

    # Check alternate locations
    for loc in work.get("locations", []):
        pdf_url = loc.get("pdf_url")
        if pdf_url:
            return pdf_url

    return None


def _map_oa_status(oa: dict[str, Any] | None) -> OpenAccessStatus:
    """Map OpenAlex OA status to our enum.

    Args:
        oa: OpenAlex open_access object.

    Returns:
        OpenAccessStatus enum value.
    """
    if not oa:
        return OpenAccessStatus.UNKNOWN

    status = oa.get("oa_status", "").lower()
    mapping = {
        "gold": OpenAccessStatus.GOLD,
        "green": OpenAccessStatus.GREEN,
        "bronze": OpenAccessStatus.BRONZE,
        "hybrid": OpenAccessStatus.HYBRID,
        "closed": OpenAccessStatus.CLOSED,
    }
    return mapping.get(status, OpenAccessStatus.UNKNOWN)


def openalex_to_reference(work: dict[str, Any]) -> ReferenceRecord:
    """Convert OpenAlex work to ReferenceRecord.

    Args:
        work: OpenAlex work object from API.

    Returns:
        ReferenceRecord with OpenAlex metadata.
    """
    # Extract DOI (remove https://doi.org/ prefix)
    doi_raw = work.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

    # Extract arXiv ID from IDs object
    ids = work.get("ids", {})
    arxiv_id = extract_arxiv_id(ids)

    # Extract authors from authorships
    authors: list[str] = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        if author.get("display_name"):
            authors.append(author["display_name"])

    # Extract venue from primary location
    primary_loc = work.get("primary_location", {}) or {}
    source = primary_loc.get("source", {}) or {}
    venue = source.get("display_name")

    # Extract concepts (top 5)
    concepts: list[str] = []
    for concept in work.get("concepts", [])[:5]:
        if concept.get("display_name"):
            concepts.append(concept["display_name"])

    # Map OA status
    oa = work.get("open_access", {})
    oa_status = _map_oa_status(oa)

    return ReferenceRecord(
        doi=doi or None,
        arxiv_id=arxiv_id,
        title=work.get("title", ""),
        authors=authors,
        year=work.get("publication_year"),
        venue=venue,
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        openalex_id=work.get("id"),
        cited_by_count=work.get("cited_by_count"),
        concepts=concepts,
        pdf_url=find_pdf_url(work),
        oa_status=oa_status,
        source="openalex",
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
        """Build request parameters with optional mailto."""
        params = dict(kwargs)
        if self.config.email:
            params["mailto"] = self.config.email
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

        return response.json()  # type: ignore[no-any-return]

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
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"ids.arxiv:{arxiv_id}")

        response = self._fetch(url, params)
        results = response.get("results", [])

        if not results:
            raise ValueError(f"No work found for arXiv:{arxiv_id}")

        return openalex_to_reference(results[0])

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
