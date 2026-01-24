"""Crossref metadata provider (SPEC-022).

Implements DOILookupProvider only (ISP compliance). arXiv lookups and
search are not supported by the Crossref API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import requests

from erdos.core.clients.crossref import fetch_crossref_work, parse_crossref_work
from erdos.core.config import AppConfig


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord


logger = logging.getLogger(__name__)


@dataclass
class CrossrefProvider:
    """DOILookupProvider implementation using Crossref API.

    ISP compliance: Only implements get_by_doi() because Crossref doesn't
    support arXiv ID lookups or search.
    """

    mailto: str
    timeout: float = 30.0

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "crossref"

    @classmethod
    def from_env(cls) -> CrossrefProvider:
        """Create provider from AppConfig (mailto + http timeout)."""
        config = AppConfig.from_env()
        return cls(mailto=config.mailto, timeout=config.http_timeout)

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """Fetch work by DOI via Crossref."""
        logger.debug("Crossref lookup by DOI: %s", doi)
        try:
            raw = fetch_crossref_work(doi, mailto=self.mailto, timeout=self.timeout)
        except requests.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None and getattr(response, "status_code", None) == 404:
                return None
            raise
        return parse_crossref_work(raw, doi=doi)
