"""Lead enrichment service (SPEC-036).

Enriches LeadRecords with metadata from FallbackProvider (OpenAlex/Crossref/arXiv).
"""

from __future__ import annotations

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
    failed: int = 0


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
                reference = self._provider.get_by_doi(doi)
            elif arxiv_id:
                reference = self._provider.get_by_arxiv(arxiv_id)

            if reference is None:
                # Provider returned nothing
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
    ) -> tuple[list[EnrichmentResult], EnrichmentStats]:
        """Enrich multiple leads in batch.

        Args:
            leads: List of LeadRecords to enrich.
            force: If True, re-enrich already enriched leads.

        Returns:
            Tuple of (results, stats).
        """
        results: list[EnrichmentResult] = []
        stats = EnrichmentStats(total=len(leads))

        for lead in leads:
            # Check if already enriched
            if lead.enriched_at is not None and not force:
                results.append(EnrichmentResult(lead=lead))
                continue

            # Check for identifiers
            has_identifier = lead.source.doi or lead.source.arxiv_id
            if has_identifier:
                stats.with_identifiers += 1
            else:
                stats.skipped_no_id += 1
                results.append(EnrichmentResult(lead=lead))
                continue

            # Enrich the lead
            result = self.enrich_lead(lead)
            results.append(result)

            if result.error:
                stats.failed += 1
            elif result.reference is not None:
                stats.enriched += 1

        return results, stats
