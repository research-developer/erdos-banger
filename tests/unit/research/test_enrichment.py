"""Tests for LeadEnrichmentService (SPEC-036).

TDD Phase 2: Lead enrichment service using FallbackProvider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from erdos.core.models import ReferenceRecord
from erdos.core.research.enrichment import (
    LeadEnrichmentService,
)
from erdos.core.research.models import LeadRecord, LeadSource


def _make_lead(
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    enriched_at: datetime | None = None,
) -> LeadRecord:
    """Create a test LeadRecord."""
    now = datetime.now(UTC)
    return LeadRecord(
        problem_id=74,
        id="lead_20260128T120000Z_abc123",
        title="Test Lead",
        source=LeadSource(doi=doi, arxiv_id=arxiv_id),
        tags=[],
        created_at=now,
        updated_at=now,
        enriched_at=enriched_at,
    )


def _make_reference(
    doi: str | None = None, arxiv_id: str | None = None
) -> ReferenceRecord:
    """Create a test ReferenceRecord."""
    return ReferenceRecord(
        doi=doi,
        arxiv_id=arxiv_id,
        title="Full Title from OpenAlex",
        authors=["Author One", "Author Two"],
        year=2023,
        venue="arXiv",
        abstract="This is the abstract.",
        source="openalex",
    )


class TestLeadEnrichmentServiceSingleLead:
    """Tests for enriching a single lead."""

    def test_enrich_lead_with_doi_success(self) -> None:
        """Lead with DOI should be enriched via FallbackProvider."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(doi="10.1234/test")
        result = service.enrich_lead(lead)

        assert result.lead.enriched_title == "Full Title from OpenAlex"
        assert result.lead.enriched_authors == ["Author One", "Author Two"]
        assert result.lead.enriched_year == 2023
        assert result.lead.enriched_venue == "arXiv"
        assert result.lead.enriched_abstract == "This is the abstract."
        assert result.lead.enriched_provider == "openalex"
        assert result.lead.enriched_at is not None
        assert result.provider == "openalex"
        assert result.error is None
        mock_provider.get_by_doi.assert_called_once_with("10.1234/test")

    def test_enrich_lead_with_arxiv_success(self) -> None:
        """Lead with arXiv ID should be enriched via FallbackProvider."""
        mock_provider = Mock()
        mock_provider.get_by_arxiv.return_value = _make_reference(arxiv_id="2305.15585")

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(arxiv_id="2305.15585")
        result = service.enrich_lead(lead)

        assert result.lead.enriched_title == "Full Title from OpenAlex"
        assert result.lead.enriched_at is not None
        assert result.provider == "openalex"
        assert result.error is None
        mock_provider.get_by_arxiv.assert_called_once_with("2305.15585")

    def test_enrich_lead_doi_takes_precedence_over_arxiv(self) -> None:
        """When both DOI and arXiv are present, DOI should be used."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(doi="10.1234/test", arxiv_id="2305.15585")
        result = service.enrich_lead(lead)

        mock_provider.get_by_doi.assert_called_once_with("10.1234/test")
        mock_provider.get_by_arxiv.assert_not_called()
        assert result.lead.enriched_title == "Full Title from OpenAlex"

    def test_enrich_lead_no_identifier_returns_unchanged(self) -> None:
        """Lead without identifiers should return unchanged."""
        mock_provider = Mock()

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(doi=None, arxiv_id=None)
        result = service.enrich_lead(lead)

        assert result.lead.enriched_at is None
        assert result.reference is None
        assert result.provider is None
        mock_provider.get_by_doi.assert_not_called()
        mock_provider.get_by_arxiv.assert_not_called()

    def test_enrich_lead_provider_returns_none(self) -> None:
        """Lead with unknown identifier should remain unenriched."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = None

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(doi="10.1234/unknown")
        result = service.enrich_lead(lead)

        assert result.lead.enriched_at is None
        assert result.reference is None
        assert result.error is None

    def test_enrich_lead_provider_error_handled(self) -> None:
        """Network errors should be caught and returned in error field."""
        mock_provider = Mock()
        mock_provider.get_by_doi.side_effect = Exception("Network error")

        service = LeadEnrichmentService(mock_provider)
        lead = _make_lead(doi="10.1234/test")
        result = service.enrich_lead(lead)

        assert result.lead.enriched_at is None
        assert result.reference is None
        assert result.error == "Network error"


class TestLeadEnrichmentServiceBatch:
    """Tests for batch lead enrichment."""

    def test_enrich_leads_batch_success(self) -> None:
        """Batch enrichment should enrich all leads with identifiers."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")
        mock_provider.get_by_arxiv.return_value = _make_reference(arxiv_id="2305.15585")

        service = LeadEnrichmentService(mock_provider)
        leads = [
            _make_lead(doi="10.1234/test"),
            _make_lead(arxiv_id="2305.15585"),
            _make_lead(),  # No identifier
        ]
        results, stats = service.enrich_leads(leads)

        assert len(results) == 3
        assert stats.total == 3
        assert stats.with_identifiers == 2
        assert stats.enriched == 2
        assert stats.skipped_no_id == 1
        assert stats.failed == 0

    def test_enrich_leads_skip_already_enriched(self) -> None:
        """Already enriched leads should be skipped unless force=True."""
        mock_provider = Mock()

        service = LeadEnrichmentService(mock_provider)
        already_enriched = _make_lead(doi="10.1234/test", enriched_at=datetime.now(UTC))
        _results, stats = service.enrich_leads([already_enriched])

        assert stats.enriched == 0
        mock_provider.get_by_doi.assert_not_called()

    def test_enrich_leads_force_re_enriches(self) -> None:
        """force=True should re-enrich already enriched leads."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        already_enriched = _make_lead(doi="10.1234/test", enriched_at=datetime.now(UTC))
        _results, stats = service.enrich_leads([already_enriched], force=True)

        assert stats.enriched == 1
        mock_provider.get_by_doi.assert_called_once()

    def test_enrich_leads_counts_failures(self) -> None:
        """Failed enrichments should be counted in stats."""
        mock_provider = Mock()
        mock_provider.get_by_doi.side_effect = Exception("Network error")

        service = LeadEnrichmentService(mock_provider)
        leads = [_make_lead(doi="10.1234/test")]
        results, stats = service.enrich_leads(leads)

        assert stats.failed == 1
        assert stats.enriched == 0
        assert results[0].error == "Network error"


class TestLeadEnrichmentServiceRateLimiting:
    """Tests for rate limiting between API calls."""

    @patch("erdos.core.research.enrichment.time.sleep")
    def test_enrich_leads_rate_limits_between_calls(self, mock_sleep: Mock) -> None:
        """Batch enrichment should sleep between API calls."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        leads = [
            _make_lead(doi="10.1234/test1"),
            _make_lead(doi="10.1234/test2"),
            _make_lead(doi="10.1234/test3"),
        ]
        service.enrich_leads(leads, delay=0.5)

        # Should sleep between calls, not before first
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    @patch("erdos.core.research.enrichment.time.sleep")
    def test_enrich_leads_no_delay_skips_sleep(self, mock_sleep: Mock) -> None:
        """delay=0 should skip sleep between calls."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        leads = [
            _make_lead(doi="10.1234/test1"),
            _make_lead(doi="10.1234/test2"),
        ]
        service.enrich_leads(leads, delay=0)

        mock_sleep.assert_not_called()

    @patch("erdos.core.research.enrichment.time.sleep")
    def test_enrich_leads_default_delay_is_one_second(self, mock_sleep: Mock) -> None:
        """Default delay should be 1.0 second."""
        mock_provider = Mock()
        mock_provider.get_by_doi.return_value = _make_reference(doi="10.1234/test")

        service = LeadEnrichmentService(mock_provider)
        leads = [
            _make_lead(doi="10.1234/test1"),
            _make_lead(doi="10.1234/test2"),
        ]
        service.enrich_leads(leads)

        mock_sleep.assert_called_with(1.0)
