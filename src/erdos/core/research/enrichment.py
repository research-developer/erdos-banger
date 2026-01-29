"""Lead enrichment service (SPEC-036).

Enriches LeadRecords with metadata from FallbackProvider (OpenAlex/Crossref/arXiv).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord
    from erdos.core.providers.fallback import FallbackProvider
    from erdos.core.research.models import LeadRecord


@dataclass
class EnrichmentResult:
    """Result of enriching a single lead."""

    lead: LeadRecord
    reference: ReferenceRecord | None = None
    provider: str | None = None
    error: str | None = None


@dataclass
class EnrichmentStats:
    """Statistics from batch enrichment."""

    total: int = 0
    with_identifiers: int = 0
    enriched: int = 0
    skipped_no_id: int = 0
    skipped_already_enriched: int = 0
    failed: int = 0


logger = logging.getLogger(__name__)


class LeadEnrichmentService:
    """Service for enriching leads with metadata from external providers.

    Uses FallbackProvider to look up DOI or arXiv ID and populate
    enrichment fields on LeadRecord.
    """

    def __init__(self, provider: FallbackProvider) -> None:
        """Initialize with a metadata provider.

        Args:
            provider: FallbackProvider instance for metadata lookups.
        """
        self._provider = provider

    def enrich_lead(self, lead: LeadRecord) -> EnrichmentResult:
        """Enrich a single lead with metadata from the provider.

        Lookup priority: DOI > arXiv ID.

        Args:
            lead: LeadRecord to enrich.

        Returns:
            EnrichmentResult with enriched lead and metadata.
        """
        # Check for identifiers
        doi = lead.source.doi
        arxiv_id = lead.source.arxiv_id

        if not doi and not arxiv_id:
            # No identifier to look up
            return EnrichmentResult(lead=lead)

        # Try to fetch metadata
        try:
            reference: ReferenceRecord | None = None
            if doi:
                logger.debug("Looking up DOI: %s", doi)
                reference = self._provider.get_by_doi(doi)
            elif arxiv_id:
                logger.debug("Looking up arXiv ID: %s", arxiv_id)
                reference = self._provider.get_by_arxiv(arxiv_id)

            if reference is None:
                # Provider returned nothing
                logger.debug("No metadata found for lead %s", lead.id)
                return EnrichmentResult(lead=lead)

            # Enrich the lead using model_copy (frozen model pattern)
            enriched_lead = lead.model_copy(
                update={
                    "enriched_title": reference.title,
                    "enriched_authors": reference.authors,
                    "enriched_year": reference.year,
                    "enriched_venue": reference.venue,
                    "enriched_abstract": reference.abstract,
                    "enriched_provider": reference.source,
                    "enriched_at": datetime.now(UTC),
                }
            )

            return EnrichmentResult(
                lead=enriched_lead,
                reference=reference,
                provider=reference.source,
            )

        except Exception as e:
            # Network or API error
            return EnrichmentResult(
                lead=lead,
                error=str(e),
            )

    def enrich_leads(
        self,
        leads: list[LeadRecord],
        *,
        force: bool = False,
        delay: float = 1.0,
    ) -> tuple[list[EnrichmentResult], EnrichmentStats]:
        """Enrich multiple leads in batch.

        Args:
            leads: List of LeadRecords to enrich.
            force: If True, re-enrich already enriched leads.
            delay: Seconds to sleep between API calls (rate limiting).

        Returns:
            Tuple of (results, stats).
        """
        results: list[EnrichmentResult] = []
        stats = EnrichmentStats(total=len(leads))
        first_api_call = True

        for lead in leads:
            # Count identifiers first (for accurate stats - BUG-050 fix)
            has_identifier = lead.source.doi or lead.source.arxiv_id
            if has_identifier:
                stats.with_identifiers += 1

            # Check if already enriched
            if lead.enriched_at is not None and not force:
                stats.skipped_already_enriched += 1
                logger.debug("Skipping already enriched lead: %s", lead.id)
                results.append(EnrichmentResult(lead=lead))
                continue

            # Check for identifiers (skip if none)
            if not has_identifier:
                stats.skipped_no_id += 1
                logger.debug("Skipping lead with no identifier: %s", lead.id)
                results.append(EnrichmentResult(lead=lead))
                continue

            # Rate limiting: sleep before API call (except first)
            if not first_api_call and delay > 0:
                time.sleep(delay)
            first_api_call = False

            # Enrich the lead
            logger.info(
                "Enriching lead %s (doi=%s, arxiv=%s)",
                lead.id,
                lead.source.doi,
                lead.source.arxiv_id,
            )
            result = self.enrich_lead(lead)
            results.append(result)

            if result.error:
                stats.failed += 1
                logger.warning("Enrichment failed for %s: %s", lead.id, result.error)
            elif result.reference is not None:
                stats.enriched += 1
                logger.info("Enriched %s via %s", lead.id, result.provider)

        return results, stats
