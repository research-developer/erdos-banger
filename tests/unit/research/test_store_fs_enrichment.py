"""Tests for FSResearchStore.lead_update() enrichment support (SPEC-036).

TDD Phase 4: Extend lead_update() to support enrichment fields.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from erdos.core.research.models import LeadStatus
from erdos.core.research.store_fs import FSResearchStore


@pytest.fixture
def store(tmp_path):
    """Create a FSResearchStore with temp directory."""
    return FSResearchStore(repo_root=tmp_path)


@pytest.fixture
def sample_lead(store):
    """Create a sample lead for testing."""
    lead, _ = store.lead_add(
        problem_id=74,
        title="Test Lead",
        doi="10.1234/test",
    )
    return lead


class TestLeadUpdateEnrichmentFields:
    """Tests for updating enrichment fields on leads."""

    def test_lead_update_enriched_title(self, store, sample_lead) -> None:
        """lead_update should accept enriched_title."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_title="Full Title from OpenAlex",
        )
        assert updated.enriched_title == "Full Title from OpenAlex"

    def test_lead_update_enriched_authors(self, store, sample_lead) -> None:
        """lead_update should accept enriched_authors list."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_authors=["Author One", "Author Two"],
        )
        assert updated.enriched_authors == ["Author One", "Author Two"]

    def test_lead_update_enriched_year(self, store, sample_lead) -> None:
        """lead_update should accept enriched_year."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_year=2023,
        )
        assert updated.enriched_year == 2023

    def test_lead_update_enriched_venue(self, store, sample_lead) -> None:
        """lead_update should accept enriched_venue."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_venue="arXiv",
        )
        assert updated.enriched_venue == "arXiv"

    def test_lead_update_enriched_abstract(self, store, sample_lead) -> None:
        """lead_update should accept enriched_abstract."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_abstract="This is the abstract text.",
        )
        assert updated.enriched_abstract == "This is the abstract text."

    def test_lead_update_enriched_provider(self, store, sample_lead) -> None:
        """lead_update should accept enriched_provider."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_provider="openalex",
        )
        assert updated.enriched_provider == "openalex"

    def test_lead_update_enriched_at(self, store, sample_lead) -> None:
        """lead_update should accept enriched_at timestamp."""
        now = datetime.now(UTC)
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_at=now,
        )
        assert updated.enriched_at == now

    def test_lead_update_all_enrichment_fields(self, store, sample_lead) -> None:
        """lead_update should accept all enrichment fields at once."""
        now = datetime.now(UTC)
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            enriched_title="Full Title",
            enriched_authors=["A", "B"],
            enriched_year=2023,
            enriched_venue="arXiv",
            enriched_abstract="Abstract",
            enriched_provider="openalex",
            enriched_at=now,
        )
        assert updated.enriched_title == "Full Title"
        assert updated.enriched_authors == ["A", "B"]
        assert updated.enriched_year == 2023
        assert updated.enriched_venue == "arXiv"
        assert updated.enriched_abstract == "Abstract"
        assert updated.enriched_provider == "openalex"
        assert updated.enriched_at == now


class TestLeadUpdateIngestFields:
    """Tests for updating ingest tracking fields on leads."""

    def test_lead_update_ingested_at(self, store, sample_lead) -> None:
        """lead_update should accept ingested_at timestamp."""
        now = datetime.now(UTC)
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            ingested_at=now,
        )
        assert updated.ingested_at == now

    def test_lead_update_manifest_entry_id(self, store, sample_lead) -> None:
        """lead_update should accept manifest_entry_id."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            manifest_entry_id="entry_abc123",
        )
        assert updated.manifest_entry_id == "entry_abc123"


class TestLeadUpdateMixedFields:
    """Tests for updating both existing and enrichment fields."""

    def test_lead_update_status_and_enrichment(self, store, sample_lead) -> None:
        """lead_update should handle both status and enrichment fields."""
        updated, _ = store.lead_update(
            74,
            sample_lead.id,
            status=LeadStatus.INVESTIGATING,
            enriched_title="Enriched Title",
        )
        assert updated.status == LeadStatus.INVESTIGATING
        assert updated.enriched_title == "Enriched Title"

    def test_lead_update_persists_to_disk(self, store, sample_lead) -> None:
        """Updated enrichment fields should persist when re-read."""
        store.lead_update(
            74,
            sample_lead.id,
            enriched_title="Persisted Title",
            enriched_provider="openalex",
        )
        # Re-read from disk
        leads = store.lead_list(74)
        lead = next(ld for ld in leads if ld.id == sample_lead.id)
        assert lead.enriched_title == "Persisted Title"
        assert lead.enriched_provider == "openalex"
