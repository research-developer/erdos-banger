"""ArXiv metadata provider (SPEC-022).

This provider fetches metadata from arXiv's API (not source content).
For downloading arXiv source tarballs, use erdos.core.ingest.arxiv_download.

Implements ArxivLookupProvider only (ISP compliance). DOI lookups and
search are not supported by the arXiv API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import defusedxml.ElementTree as ET

from erdos.core.clients.arxiv import fetch_arxiv_atom, parse_arxiv_atom


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


class ArxivProvider:
    """ArxivLookupProvider implementation using arXiv API.

    Note: This is for METADATA only (title, authors, abstract).
    Does not download source tarballs - use ingest.arxiv_download for that.

    ISP compliance: Only implements get_by_arxiv() because arXiv API
    doesn't support DOI lookups or search.
    """

    timeout: float

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize with HTTP timeout."""
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "arxiv"

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None:
        """Fetch metadata by arXiv ID via arXiv API.

        Raises:
            requests.RequestException: On network errors.
            ValueError: On parsing errors (converted from ParseError).
        """
        logger.debug("arXiv lookup: %s", arxiv_id)
        atom_xml = fetch_arxiv_atom(arxiv_id, timeout=self.timeout)
        try:
            return parse_arxiv_atom(atom_xml)
        except ET.ParseError as e:
            # Convert ParseError to ValueError per ArxivLookupProvider contract
            raise ValueError(
                f"Failed to parse arXiv response for {arxiv_id}: {e}"
            ) from e
