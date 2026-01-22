"""Fallback metadata provider chain (SPEC-022).

ISP-compliant router that composes three independent capability chains:
- DOI chain: list[DOILookupProvider]
- arXiv chain: list[ArxivLookupProvider]
- search chain: list[SearchableMetadataProvider]

This allows providers to implement only the capabilities they support.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord
    from erdos.core.ports import (
        ArxivLookupProvider,
        DOILookupProvider,
        SearchableMetadataProvider,
    )


logger = logging.getLogger(__name__)

# Expected exception types per provider protocol contract (ports.py):
# - requests.RequestException: network/API errors (non-404)
# - ValueError: invalid identifiers or irrecoverable parse errors
# Unknown exceptions propagate (fail fast on programming errors).
_EXPECTED_PROVIDER_ERRORS = (requests.RequestException, ValueError)


class FallbackProvider:
    """MetadataProvider that routes to capability-specific fallback chains.

    ISP-compliant: each lookup method uses only providers that support
    that capability. Providers no longer need stub methods for unsupported
    operations.

    Example:
        provider = FallbackProvider(
            doi_chain=[OpenAlexProvider.from_env(), CrossrefProvider.from_env()],
            arxiv_chain=[OpenAlexProvider.from_env(), ArxivProvider()],
            search_chain=[OpenAlexProvider.from_env()],
        )
        # DOI lookups try OpenAlex → Crossref
        # arXiv lookups try OpenAlex → arXiv
        # Search uses OpenAlex only
    """

    __slots__ = ("_arxiv_chain", "_doi_chain", "_name", "_search_chain")

    def __init__(
        self,
        *,
        doi_chain: list[DOILookupProvider],
        arxiv_chain: list[ArxivLookupProvider],
        search_chain: list[SearchableMetadataProvider],
    ) -> None:
        """Initialize with capability-specific chains.

        Args:
            doi_chain: Providers for DOI lookup (in priority order).
            arxiv_chain: Providers for arXiv lookup (in priority order).
            search_chain: Providers for search (in priority order).

        Raises:
            ValueError: If all chains are empty.
        """
        if not doi_chain and not arxiv_chain and not search_chain:
            raise ValueError("FallbackProvider requires at least one provider chain")
        self._doi_chain = list(doi_chain)
        self._arxiv_chain = list(arxiv_chain)
        self._search_chain = list(search_chain)
        self._name = self._build_name()

    def _build_name(self) -> str:
        """Build human-readable name showing the capability chains."""
        parts = []
        if self._doi_chain:
            doi_names = " -> ".join(p.provider_name for p in self._doi_chain)
            parts.append(f"doi:{doi_names}")
        if self._arxiv_chain:
            arxiv_names = " -> ".join(p.provider_name for p in self._arxiv_chain)
            parts.append(f"arxiv:{arxiv_names}")
        if self._search_chain:
            search_names = " -> ".join(p.provider_name for p in self._search_chain)
            parts.append(f"search:{search_names}")
        return f"fallback({', '.join(parts)})"

    @property
    def provider_name(self) -> str:
        """Human-readable name showing the capability chains."""
        return self._name

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Try each DOI provider in order until one returns a result."""
        for provider in self._doi_chain:
            try:
                result = provider.get_by_doi(doi)
                if result is not None:
                    logger.debug("DOI %s resolved by %s", doi, provider.provider_name)
                    return result
                logger.debug(
                    "DOI %s not found in %s, trying next", doi, provider.provider_name
                )
            except _EXPECTED_PROVIDER_ERRORS:
                logger.warning(
                    "Provider %s failed for DOI %s, trying next",
                    provider.provider_name,
                    doi,
                    exc_info=True,
                )
        logger.debug("DOI %s not found in any provider", doi)
        return None

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Try each arXiv provider in order until one returns a result."""
        for provider in self._arxiv_chain:
            try:
                result = provider.get_by_arxiv(arxiv_id)
                if result is not None:
                    logger.debug(
                        "arXiv %s resolved by %s", arxiv_id, provider.provider_name
                    )
                    return result
                logger.debug(
                    "arXiv %s not found in %s, trying next",
                    arxiv_id,
                    provider.provider_name,
                )
            except _EXPECTED_PROVIDER_ERRORS:
                logger.warning(
                    "Provider %s failed for arXiv %s, trying next",
                    provider.provider_name,
                    arxiv_id,
                    exc_info=True,
                )
        logger.debug("arXiv %s not found in any provider", arxiv_id)
        return None

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Use first search provider that returns non-empty results."""
        for provider in self._search_chain:
            try:
                results = provider.search(query, limit=limit)
                if results:
                    logger.debug(
                        "Search '%s' returned %d results from %s",
                        query,
                        len(results),
                        provider.provider_name,
                    )
                    return results
            except _EXPECTED_PROVIDER_ERRORS:
                logger.warning(
                    "Provider %s failed for search '%s', trying next",
                    provider.provider_name,
                    query,
                    exc_info=True,
                )
        logger.debug("Search '%s' returned no results from any provider", query)
        return []
