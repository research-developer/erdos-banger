"""Integration tests for lead enrichment pipeline (SPEC-036).

These tests verify the full pipeline with real components:
- Real FSResearchStore with actual file I/O
- Real ManifestBridge with actual deduplication logic
- Real LeadEnrichmentService
- Only mocks: FallbackProvider (HTTP boundary)

Rob C. Martin approved: mock at the port boundary, test real behavior.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from erdos.core.models import ProblemManifest, ReferenceRecord
from erdos.core.research import FSResearchStore
from erdos.core.research.enrichment import LeadEnrichmentService
from erdos.core.research.manifest_bridge import ManifestBridge


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Create a temp repo structure for integration tests."""
    # Create minimal structure
    (tmp_path / "research" / "74" / "leads").mkdir(parents=True)
    (tmp_path / "literature" / "manifests").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_provider() -> Mock:
    """Create a mock FallbackProvider (network boundary mock only)."""
    provider = Mock()

    def get_by_doi(doi: str) -> ReferenceRecord | None:
        """Return realistic metadata for test DOIs."""
        if doi == "10.1234/test-paper":
            return ReferenceRecord(
                doi=doi,
                title="A Test Paper on Number Theory",
                authors=["Alice Smith", "Bob Jones"],
                year=2023,
                venue="Journal of Mathematics",
                abstract="This paper proves results about primes.",
                source="openalex",
            )
        return None  # Unknown DOI

    def get_by_arxiv(arxiv_id: str) -> ReferenceRecord | None:
        """Return realistic metadata for test arXiv IDs."""
        if arxiv_id == "2305.15585":
            return ReferenceRecord(
                arxiv_id=arxiv_id,
                title="Prime Number Results",
                authors=["Charlie Brown"],
                year=2023,
                venue="arXiv",
                abstract="We discuss prime numbers.",
                source="openalex",
            )
        return None  # Unknown arXiv ID

    provider.get_by_doi.side_effect = get_by_doi
    provider.get_by_arxiv.side_effect = get_by_arxiv
    return provider


class TestLeadEnrichmentPipelineIntegration:
    """Integration tests for the full enrichment pipeline."""

    def test_full_pipeline_add_enrich_ingest(
        self, repo_root: Path, mock_provider: Mock
    ) -> None:
        """Test full pipeline: add leads → enrich → ingest to manifest.

        This tests real behavior with actual file I/O and object interactions.
        Only the HTTP calls to OpenAlex/Crossref are mocked.
        """
        # Step 1: Add leads using real FSResearchStore
        store = FSResearchStore(repo_root=repo_root)

        _lead1, path1 = store.lead_add(
            problem_id=74,
            title="Test Lead 1",
            doi="10.1234/test-paper",
        )
        _lead2, path2 = store.lead_add(
            problem_id=74,
            title="Test Lead 2",
            arxiv_id="2305.15585",
        )
        _lead3, _path3 = store.lead_add(
            problem_id=74,
            title="Test Lead 3 (no identifier)",
        )

        # Verify files were actually written
        assert path1.exists()
        assert path2.exists()

        # Step 2: Enrich leads using real LeadEnrichmentService
        service = LeadEnrichmentService(mock_provider)
        leads = store.lead_list(74)
        assert len(leads) == 3

        results, stats = service.enrich_leads(leads, delay=0)  # No delay for tests

        # Verify enrichment stats
        assert stats.total == 3
        assert stats.with_identifiers == 2
        assert stats.enriched == 2
        assert stats.skipped_no_id == 1
        assert stats.failed == 0

        # Step 3: Persist enriched leads back to store
        for result in results:
            if result.lead.enriched_at is not None:
                store.lead_update(
                    74,
                    result.lead.id,
                    enriched_title=result.lead.enriched_title,
                    enriched_authors=result.lead.enriched_authors,
                    enriched_year=result.lead.enriched_year,
                    enriched_venue=result.lead.enriched_venue,
                    enriched_abstract=result.lead.enriched_abstract,
                    enriched_provider=result.lead.enriched_provider,
                    enriched_at=result.lead.enriched_at,
                )

        # Verify enrichment persisted to disk
        persisted_leads = store.lead_list(74)
        enriched_leads = [ld for ld in persisted_leads if ld.enriched_at is not None]
        assert len(enriched_leads) == 2

        # Step 4: Ingest enriched leads into manifest
        bridge = ManifestBridge()
        manifest = ProblemManifest(problem_id=74, entries=[])

        _ingest_results, ingest_stats, updated_manifest = bridge.ingest_leads(
            enriched_leads, manifest
        )

        # Verify ingestion results
        assert ingest_stats.total == 2
        assert ingest_stats.added == 2
        assert ingest_stats.skipped_duplicate == 0
        assert len(updated_manifest.entries) == 2

        # Verify manifest entries have correct data
        entries_by_doi = {
            e.reference.doi: e for e in updated_manifest.entries if e.reference.doi
        }
        assert "10.1234/test-paper" in entries_by_doi
        entry = entries_by_doi["10.1234/test-paper"]
        assert entry.reference.title == "A Test Paper on Number Theory"
        assert entry.reference.authors == ["Alice Smith", "Bob Jones"]
        assert entry.source == "lead"
        assert entry.lead_id is not None

    def test_deduplication_across_runs(
        self, repo_root: Path, mock_provider: Mock
    ) -> None:
        """Test that re-running ingestion deduplicates correctly."""
        store = FSResearchStore(repo_root=repo_root)

        # Add and enrich first lead
        lead1, _ = store.lead_add(
            problem_id=74, title="Lead 1", doi="10.1234/test-paper"
        )

        service = LeadEnrichmentService(mock_provider)
        results, _ = service.enrich_leads([lead1], delay=0)

        # Persist enrichment
        result = results[0]
        store.lead_update(
            74,
            result.lead.id,
            enriched_title=result.lead.enriched_title,
            enriched_at=result.lead.enriched_at,
        )

        # First ingestion
        bridge = ManifestBridge()
        manifest = ProblemManifest(problem_id=74, entries=[])
        enriched_leads = [ld for ld in store.lead_list(74) if ld.enriched_at]
        _, stats1, manifest = bridge.ingest_leads(enriched_leads, manifest)

        assert stats1.added == 1
        assert len(manifest.entries) == 1

        # Add second lead with SAME DOI
        lead2, _ = store.lead_add(
            problem_id=74, title="Lead 2", doi="10.1234/test-paper"
        )
        results2, _ = service.enrich_leads([lead2], delay=0)
        result2 = results2[0]
        store.lead_update(
            74,
            result2.lead.id,
            enriched_title=result2.lead.enriched_title,
            enriched_at=result2.lead.enriched_at,
        )

        # Second ingestion - should skip duplicate
        enriched_leads = [ld for ld in store.lead_list(74) if ld.enriched_at]
        _, stats2, final_manifest = bridge.ingest_leads(enriched_leads, manifest)

        # The new lead should be skipped as duplicate
        assert stats2.skipped_duplicate >= 1
        assert len(final_manifest.entries) == 1  # Still just 1 entry

    def test_enrichment_with_provider_failure(self, repo_root: Path) -> None:
        """Test pipeline handles provider failures gracefully."""
        store = FSResearchStore(repo_root=repo_root)

        # Add lead with DOI that will fail
        lead, _ = store.lead_add(
            problem_id=74, title="Lead 1", doi="10.1234/failing-doi"
        )

        # Provider that fails
        failing_provider = Mock()
        failing_provider.get_by_doi.side_effect = Exception("Network timeout")

        service = LeadEnrichmentService(failing_provider)
        results, stats = service.enrich_leads([lead], delay=0)

        # Should record failure, not crash
        assert stats.failed == 1
        assert stats.enriched == 0
        assert results[0].error == "Network timeout"
        assert results[0].lead.enriched_at is None

    def test_force_re_enrichment(self, repo_root: Path, mock_provider: Mock) -> None:
        """Test that force=True re-enriches already enriched leads."""
        store = FSResearchStore(repo_root=repo_root)

        # Add and enrich lead
        lead, _ = store.lead_add(
            problem_id=74, title="Lead 1", doi="10.1234/test-paper"
        )

        service = LeadEnrichmentService(mock_provider)
        results, _ = service.enrich_leads([lead], delay=0)

        # Persist enrichment
        result = results[0]
        store.lead_update(
            74,
            result.lead.id,
            enriched_title=result.lead.enriched_title,
            enriched_at=result.lead.enriched_at,
        )

        # Re-read and try to enrich again without force
        leads = store.lead_list(74)
        mock_provider.get_by_doi.reset_mock()

        _, stats1 = service.enrich_leads(leads, delay=0, force=False)
        assert stats1.enriched == 0  # Skipped because already enriched
        mock_provider.get_by_doi.assert_not_called()

        # Now with force=True
        _, stats2 = service.enrich_leads(leads, delay=0, force=True)
        assert stats2.enriched == 1  # Re-enriched
        mock_provider.get_by_doi.assert_called()
