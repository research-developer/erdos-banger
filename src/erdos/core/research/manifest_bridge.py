"""Manifest bridge for lead ingestion (SPEC-036).

Converts enriched LeadRecords to ManifestEntries with deduplication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from erdos.core.models import ManifestEntry, ReferenceRecord


def _normalize_doi(doi: str) -> str:
    """Normalize DOI for case-insensitive comparison (BUG-051 fix).

    DOIs are case-insensitive per DOI handbook section 2.4.
    """
    return doi.lower()


def _normalize_arxiv_id(arxiv_id: str) -> str:
    """Normalize arXiv ID by stripping version suffix (BUG-052 fix).

    '2305.15585v2' -> '2305.15585'
    Versions are different revisions of the same paper.
    """
    return re.sub(r"v\d+$", "", arxiv_id)


if TYPE_CHECKING:
    from erdos.core.models import ProblemManifest
    from erdos.core.research.models import LeadRecord


@dataclass
class IngestResult:
    """Result of ingesting a single lead into manifest."""

    lead_id: str
    entry: ManifestEntry | None = None
    added: bool = False
    reason: str | None = None


@dataclass
class IngestStats:
    """Statistics from batch ingestion."""

    total: int = 0
    added: int = 0
    skipped_duplicate: int = 0
    skipped_not_enriched: int = 0
    skipped_no_identifier: int = 0


class ManifestBridge:
    """Bridges enriched leads to manifest entries.

    Handles:
    - Converting LeadRecord enrichment data to ReferenceRecord
    - Deduplication by DOI and arXiv ID
    - Tracking source provenance (lead_id)
    """

    def ingest_lead(
        self,
        lead: LeadRecord,
        manifest: ProblemManifest,
        seen_dois: set[str] | None = None,
        seen_arxiv_ids: set[str] | None = None,
    ) -> IngestResult:
        """Ingest a single enriched lead into the manifest.

        Args:
            lead: Enriched LeadRecord to ingest.
            manifest: Existing manifest to check for duplicates.
            seen_dois: Set of DOIs already seen in this batch.
            seen_arxiv_ids: Set of arXiv IDs already seen in this batch.

        Returns:
            IngestResult with entry if added, reason if skipped.
        """
        seen_dois = seen_dois or set()
        seen_arxiv_ids = seen_arxiv_ids or set()

        # Check if enriched
        if lead.enriched_at is None:
            return IngestResult(
                lead_id=lead.id,
                added=False,
                reason="not_enriched",
            )

        # Get identifiers
        doi = lead.source.doi
        arxiv_id = lead.source.arxiv_id

        # Check for identifier
        if not doi and not arxiv_id:
            return IngestResult(
                lead_id=lead.id,
                added=False,
                reason="no_identifier",
            )

        # Build lookup sets from existing manifest (normalized - BUG-051, BUG-052 fix)
        existing_dois = {
            _normalize_doi(e.reference.doi) for e in manifest.entries if e.reference.doi
        }
        existing_arxiv_ids = {
            _normalize_arxiv_id(e.reference.arxiv_id)
            for e in manifest.entries
            if e.reference.arxiv_id
        }

        # Check for duplicate DOI (case-insensitive - BUG-051 fix)
        if doi and (
            _normalize_doi(doi) in existing_dois or _normalize_doi(doi) in seen_dois
        ):
            return IngestResult(
                lead_id=lead.id,
                added=False,
                reason="duplicate_doi",
            )

        # Check for duplicate arXiv ID (version-normalized - BUG-052 fix)
        if arxiv_id and (
            _normalize_arxiv_id(arxiv_id) in existing_arxiv_ids
            or _normalize_arxiv_id(arxiv_id) in seen_arxiv_ids
        ):
            return IngestResult(
                lead_id=lead.id,
                added=False,
                reason="duplicate_arxiv",
            )

        # Create ReferenceRecord from enriched data
        reference = ReferenceRecord(
            doi=doi,
            arxiv_id=arxiv_id,
            title=lead.enriched_title or lead.title,
            authors=lead.enriched_authors or [],
            year=lead.enriched_year,
            venue=lead.enriched_venue,
            abstract=lead.enriched_abstract,
            source=lead.enriched_provider,
        )

        # Create ManifestEntry with provenance
        entry = ManifestEntry(
            reference=reference,
            source="lead",
            lead_id=lead.id,
        )

        return IngestResult(
            lead_id=lead.id,
            entry=entry,
            added=True,
        )

    def ingest_leads(
        self,
        leads: list[LeadRecord],
        manifest: ProblemManifest,
    ) -> tuple[list[IngestResult], IngestStats, ProblemManifest]:
        """Ingest multiple leads into the manifest.

        Args:
            leads: List of LeadRecords to ingest.
            manifest: Existing manifest.

        Returns:
            Tuple of (results, stats, updated_manifest).
        """
        results: list[IngestResult] = []
        stats = IngestStats(total=len(leads))

        # Track seen identifiers within this batch
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()

        # Collect new entries
        new_entries: list[ManifestEntry] = []

        for lead in leads:
            result = self.ingest_lead(lead, manifest, seen_dois, seen_arxiv_ids)
            results.append(result)

            if result.added and result.entry is not None:
                stats.added += 1
                new_entries.append(result.entry)
                # Track for batch dedup (normalized - BUG-051, BUG-052 fix)
                if lead.source.doi:
                    seen_dois.add(_normalize_doi(lead.source.doi))
                if lead.source.arxiv_id:
                    seen_arxiv_ids.add(_normalize_arxiv_id(lead.source.arxiv_id))
            elif result.reason == "not_enriched":
                stats.skipped_not_enriched += 1
            elif result.reason == "no_identifier":
                stats.skipped_no_identifier += 1
            elif result.reason in ("duplicate_doi", "duplicate_arxiv"):
                stats.skipped_duplicate += 1

        # Create updated manifest
        updated_manifest = manifest.model_copy(
            update={
                "entries": manifest.entries + new_entries,
                "updated_at": datetime.now(UTC),
            }
        )

        return results, stats, updated_manifest
