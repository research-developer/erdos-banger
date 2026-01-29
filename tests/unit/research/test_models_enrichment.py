"""Tests for LeadRecord and ManifestEntry enrichment extensions (SPEC-036).

TDD Phase 1: Model extensions for lead enrichment pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from erdos.core.models import ManifestEntry, ReferenceRecord
from erdos.core.research.models import LeadRecord, LeadSource


class TestLeadRecordEnrichmentFields:
    """Tests for enrichment fields on LeadRecord."""

    def test_lead_record_has_enrichment_fields_with_none_defaults(self) -> None:
        """LeadRecord should have all enrichment fields with None defaults."""
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_20260128T120000Z_abc123",
            title="Test Lead",
            source=LeadSource(),
            tags=[],
            created_at=now,
            updated_at=now,
        )
        # All enrichment fields should exist and default to None
        assert lead.enriched_title is None
        assert lead.enriched_authors is None
        assert lead.enriched_year is None
        assert lead.enriched_venue is None
        assert lead.enriched_abstract is None
        assert lead.enriched_provider is None
        assert lead.enriched_at is None

    def test_lead_record_has_ingest_tracking_fields(self) -> None:
        """LeadRecord should have ingested_at and manifest_entry_id."""
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_20260128T120000Z_abc123",
            title="Test Lead",
            source=LeadSource(),
            tags=[],
            created_at=now,
            updated_at=now,
        )
        assert lead.ingested_at is None
        assert lead.manifest_entry_id is None

    def test_lead_record_enrichment_fields_can_be_set(self) -> None:
        """LeadRecord should accept enrichment field values."""
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_20260128T120000Z_abc123",
            title="Test Lead",
            source=LeadSource(arxiv_id="2305.15585"),
            tags=[],
            created_at=now,
            updated_at=now,
            enriched_title="Full Title from OpenAlex",
            enriched_authors=["Author One", "Author Two"],
            enriched_year=2023,
            enriched_venue="arXiv",
            enriched_abstract="This is the abstract.",
            enriched_provider="openalex",
            enriched_at=now,
            ingested_at=now,
            manifest_entry_id="entry_123",
        )
        assert lead.enriched_title == "Full Title from OpenAlex"
        assert lead.enriched_authors == ["Author One", "Author Two"]
        assert lead.enriched_year == 2023
        assert lead.enriched_venue == "arXiv"
        assert lead.enriched_abstract == "This is the abstract."
        assert lead.enriched_provider == "openalex"
        assert lead.enriched_at == now
        assert lead.ingested_at == now
        assert lead.manifest_entry_id == "entry_123"

    def test_lead_record_model_copy_with_enrichment(self) -> None:
        """LeadRecord.model_copy() should work with enrichment updates."""
        now = datetime.now(UTC)
        lead = LeadRecord(
            problem_id=74,
            id="lead_20260128T120000Z_abc123",
            title="Test Lead",
            source=LeadSource(arxiv_id="2305.15585"),
            tags=[],
            created_at=now,
            updated_at=now,
        )
        # Use model_copy to update enrichment fields (frozen model pattern)
        enriched = lead.model_copy(
            update={
                "enriched_title": "Enriched Title",
                "enriched_provider": "openalex",
                "enriched_at": now,
            }
        )
        assert enriched.enriched_title == "Enriched Title"
        assert enriched.enriched_provider == "openalex"
        assert enriched.enriched_at == now
        # Original should be unchanged
        assert lead.enriched_title is None

    def test_existing_leads_without_enrichment_fields_still_validate(self) -> None:
        """Backward compatibility: leads from disk without new fields should validate."""
        # Simulate loading a lead dict that doesn't have the new fields
        lead_dict = {
            "schema_version": 1,
            "problem_id": 74,
            "id": "lead_20260128T120000Z_abc123",
            "title": "Old Lead",
            "status": "new",
            "priority": "medium",
            "tags": [],
            "source": {"doi": None, "arxiv_id": None, "url": None},
            "notes": "",
            "created_at": "2026-01-28T12:00:00Z",
            "updated_at": "2026-01-28T12:00:00Z",
            # NOTE: No enrichment fields - simulates old lead on disk
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(LeadRecord)
        lead = adapter.validate_python(lead_dict, strict=False)
        assert lead.enriched_title is None
        assert lead.ingested_at is None


class TestManifestEntrySourceTracking:
    """Tests for source tracking fields on ManifestEntry."""

    def test_manifest_entry_has_source_field_with_default(self) -> None:
        """ManifestEntry should have source field defaulting to 'problem_ref'."""
        entry = ManifestEntry(
            reference=ReferenceRecord(
                doi="10.1234/test",
                title="Test Reference",
            )
        )
        assert entry.source == "problem_ref"

    def test_manifest_entry_has_lead_id_field(self) -> None:
        """ManifestEntry should have lead_id field defaulting to None."""
        entry = ManifestEntry(
            reference=ReferenceRecord(
                doi="10.1234/test",
                title="Test Reference",
            )
        )
        assert entry.lead_id is None

    def test_manifest_entry_source_can_be_lead(self) -> None:
        """ManifestEntry should accept source='lead' with lead_id."""
        entry = ManifestEntry(
            reference=ReferenceRecord(
                arxiv_id="2305.15585",
                title="Test Reference from Lead",
            ),
            source="lead",
            lead_id="lead_20260128T120000Z_abc123",
        )
        assert entry.source == "lead"
        assert entry.lead_id == "lead_20260128T120000Z_abc123"

    def test_manifest_entry_rejects_invalid_source(self) -> None:
        """ManifestEntry should reject invalid source values."""
        with pytest.raises(ValueError):
            ManifestEntry(
                reference=ReferenceRecord(
                    doi="10.1234/test",
                    title="Test Reference",
                ),
                source="invalid_source",  # type: ignore[arg-type]
            )

    def test_existing_manifests_without_source_field_still_validate(self) -> None:
        """Backward compatibility: manifests without source field should validate."""
        entry_dict = {
            "schema_version": 1,
            "reference": {
                "doi": "10.1234/test",
                "title": "Old Entry",
                "authors": [],
            },
            "cached": False,
            "extracted": False,
            # NOTE: No source or lead_id - simulates old entry on disk
        }
        from pydantic import TypeAdapter

        adapter = TypeAdapter(ManifestEntry)
        entry = adapter.validate_python(entry_dict, strict=False)
        assert entry.source == "problem_ref"  # Default
        assert entry.lead_id is None
