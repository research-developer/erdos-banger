"""Tests for ManifestBridge (SPEC-036).

TDD Phase 3: Bridge between enriched leads and manifest entries.
"""

from __future__ import annotations

from datetime import UTC, datetime

from erdos.core.models import ManifestEntry, ProblemManifest, ReferenceRecord
from erdos.core.research.manifest_bridge import (
    ManifestBridge,
)
from erdos.core.research.models import LeadRecord, LeadSource


def _make_enriched_lead(
    *,
    lead_id: str = "lead_abc123",
    doi: str | None = None,
    arxiv_id: str | None = None,
) -> LeadRecord:
    """Create an enriched LeadRecord for testing."""
    now = datetime.now(UTC)
    return LeadRecord(
        problem_id=74,
        id=lead_id,
        title="Original Lead Title",
        source=LeadSource(doi=doi, arxiv_id=arxiv_id),
        tags=[],
        created_at=now,
        updated_at=now,
        enriched_title="Enriched Title from OpenAlex",
        enriched_authors=["Author A", "Author B"],
        enriched_year=2023,
        enriched_venue="arXiv",
        enriched_abstract="The abstract text.",
        enriched_provider="openalex",
        enriched_at=now,
    )


def _make_manifest(entries: list[ManifestEntry] | None = None) -> ProblemManifest:
    """Create a test ProblemManifest."""
    return ProblemManifest(
        problem_id=74,
        entries=entries or [],
    )


def _make_entry(
    *, doi: str | None = None, arxiv_id: str | None = None
) -> ManifestEntry:
    """Create a test ManifestEntry."""
    return ManifestEntry(
        reference=ReferenceRecord(
            doi=doi,
            arxiv_id=arxiv_id,
            title="Existing Reference",
        )
    )


class TestManifestBridgeBasic:
    """Tests for basic ManifestBridge operations."""

    def test_ingest_lead_creates_manifest_entry(self) -> None:
        """Ingesting an enriched lead should create a ManifestEntry."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        lead = _make_enriched_lead(doi="10.1234/test")

        result = bridge.ingest_lead(lead, manifest)

        assert result.entry is not None
        assert result.entry.reference.doi == "10.1234/test"
        assert result.entry.reference.title == "Enriched Title from OpenAlex"
        assert result.entry.reference.authors == ["Author A", "Author B"]
        assert result.entry.reference.year == 2023
        assert result.entry.source == "lead"
        assert result.entry.lead_id == "lead_abc123"
        assert result.added is True
        assert result.reason is None

    def test_ingest_lead_with_arxiv_id(self) -> None:
        """Lead with arXiv ID should create proper entry."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        lead = _make_enriched_lead(arxiv_id="2305.15585")

        result = bridge.ingest_lead(lead, manifest)

        assert result.entry is not None
        assert result.entry.reference.arxiv_id == "2305.15585"
        assert result.added is True

    def test_ingest_lead_not_enriched_skipped(self) -> None:
        """Lead without enrichment should be skipped."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_not_enriched",
            title="Not Enriched",
            source=LeadSource(doi="10.1234/test"),
            tags=[],
            created_at=now,
            updated_at=now,
            # No enriched_at = not enriched
        )

        result = bridge.ingest_lead(lead, manifest)

        assert result.entry is None
        assert result.added is False
        assert result.reason == "not_enriched"

    def test_ingest_lead_no_identifier_skipped(self) -> None:
        """Lead without DOI or arXiv ID should be skipped."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_no_id",
            title="No Identifier",
            source=LeadSource(),  # No identifiers
            tags=[],
            created_at=now,
            updated_at=now,
            enriched_at=now,  # Enriched but no identifier
        )

        result = bridge.ingest_lead(lead, manifest)

        assert result.entry is None
        assert result.added is False
        assert result.reason == "no_identifier"


class TestManifestBridgeDeduplication:
    """Tests for deduplication logic."""

    def test_ingest_lead_duplicate_doi_skipped(self) -> None:
        """Lead with DOI already in manifest should be skipped."""
        bridge = ManifestBridge()
        existing_entry = _make_entry(doi="10.1234/existing")
        manifest = _make_manifest(entries=[existing_entry])
        lead = _make_enriched_lead(doi="10.1234/existing")

        result = bridge.ingest_lead(lead, manifest)

        assert result.added is False
        assert result.reason == "duplicate_doi"

    def test_ingest_lead_duplicate_arxiv_skipped(self) -> None:
        """Lead with arXiv ID already in manifest should be skipped."""
        bridge = ManifestBridge()
        existing_entry = _make_entry(arxiv_id="2305.15585")
        manifest = _make_manifest(entries=[existing_entry])
        lead = _make_enriched_lead(arxiv_id="2305.15585")

        result = bridge.ingest_lead(lead, manifest)

        assert result.added is False
        assert result.reason == "duplicate_arxiv"

    def test_ingest_lead_unique_doi_added(self) -> None:
        """Lead with new DOI should be added."""
        bridge = ManifestBridge()
        existing_entry = _make_entry(doi="10.1234/old")
        manifest = _make_manifest(entries=[existing_entry])
        lead = _make_enriched_lead(doi="10.1234/new")

        result = bridge.ingest_lead(lead, manifest)

        assert result.added is True
        assert result.entry is not None


class TestManifestBridgeBatch:
    """Tests for batch ingestion."""

    def test_ingest_leads_batch(self) -> None:
        """Batch ingestion should process multiple leads."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        leads = [
            _make_enriched_lead(lead_id="lead_1", doi="10.1234/one"),
            _make_enriched_lead(lead_id="lead_2", arxiv_id="2305.11111"),
            _make_enriched_lead(lead_id="lead_3", doi="10.1234/three"),
        ]

        results, stats, updated_manifest = bridge.ingest_leads(leads, manifest)

        assert len(results) == 3
        assert stats.total == 3
        assert stats.added == 3
        assert stats.skipped_duplicate == 0
        assert len(updated_manifest.entries) == 3

    def test_ingest_leads_deduplicates_within_batch(self) -> None:
        """Batch should deduplicate leads against each other."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        leads = [
            _make_enriched_lead(lead_id="lead_1", doi="10.1234/same"),
            _make_enriched_lead(lead_id="lead_2", doi="10.1234/same"),  # Duplicate
        ]

        _results, stats, updated_manifest = bridge.ingest_leads(leads, manifest)

        assert stats.added == 1
        assert stats.skipped_duplicate == 1
        assert len(updated_manifest.entries) == 1

    def test_ingest_leads_stats_breakdown(self) -> None:
        """Stats should correctly categorize outcomes."""
        bridge = ManifestBridge()
        existing_entry = _make_entry(doi="10.1234/existing")
        manifest = _make_manifest(entries=[existing_entry])

        now = datetime.now(UTC)
        not_enriched = LeadRecord(
            problem_id=74,
            id="lead_not_enriched",
            title="Not Enriched",
            source=LeadSource(doi="10.1234/new"),
            tags=[],
            created_at=now,
            updated_at=now,
        )
        leads = [
            _make_enriched_lead(lead_id="lead_1", doi="10.1234/new"),  # Added
            _make_enriched_lead(lead_id="lead_2", doi="10.1234/existing"),  # Dup
            not_enriched,  # Not enriched
        ]

        _results, stats, _ = bridge.ingest_leads(leads, manifest)

        assert stats.total == 3
        assert stats.added == 1
        assert stats.skipped_duplicate == 1
        assert stats.skipped_not_enriched == 1

    def test_ingest_leads_updates_manifest_timestamp(self) -> None:
        """Updated manifest should have new updated_at timestamp."""
        bridge = ManifestBridge()
        manifest = _make_manifest()
        old_updated = manifest.updated_at
        leads = [_make_enriched_lead(doi="10.1234/test")]

        _, _, updated_manifest = bridge.ingest_leads(leads, manifest)

        assert updated_manifest.updated_at >= old_updated
