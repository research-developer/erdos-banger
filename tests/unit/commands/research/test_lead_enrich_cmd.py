"""Tests for `erdos research lead enrich` command (SPEC-036).

TDD Phase 5: CLI command for lead enrichment.
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from erdos.core.research.enrichment import EnrichmentResult, EnrichmentStats
from erdos.core.research.models import LeadRecord, LeadSource


runner = CliRunner()


@pytest.fixture
def mock_leads() -> list[LeadRecord]:
    """Create mock leads for testing."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return [
        LeadRecord(
            problem_id=74,
            id="lead_001",
            title="Lead One",
            source=LeadSource(doi="10.1234/one"),
            tags=[],
            created_at=now,
            updated_at=now,
        ),
        LeadRecord(
            problem_id=74,
            id="lead_002",
            title="Lead Two",
            source=LeadSource(arxiv_id="2305.15585"),
            tags=[],
            created_at=now,
            updated_at=now,
        ),
    ]


class TestLeadEnrichHelp:
    """Tests for command help and basic invocation."""

    def test_enrich_help_shows_usage(self, strip_ansi: Callable[[str], str]) -> None:
        """--help should show command usage."""
        result = runner.invoke(app, ["research", "lead", "enrich", "--help"])
        output = strip_ansi(result.output)
        assert "Enrich leads" in output or "enrich" in output.lower()
        assert "--force" in output
        assert "--dry-run" in output

    def test_enrich_requires_problem_id(self, strip_ansi: Callable[[str], str]) -> None:
        """Command should require problem_id argument."""
        result = runner.invoke(app, ["research", "lead", "enrich"])
        output = strip_ansi(result.output)
        # Should show missing argument error
        assert result.exit_code != 0


class TestLeadEnrichDryRun:
    """Tests for --dry-run mode."""

    @patch("erdos.commands.research.lead.get_app_context")
    @patch("erdos.commands.research.lead.FSResearchStore")
    def test_enrich_dry_run_shows_preview(
        self,
        mock_store_cls: Mock,
        mock_get_ctx: Mock,
        mock_leads: list[LeadRecord],
        strip_ansi: Callable[[str], str],
    ) -> None:
        """--dry-run should show what would be enriched."""
        # Setup mocks
        mock_ctx = Mock()
        mock_ctx.problems.get.return_value = Mock(id=74, title="Test Problem")
        mock_get_ctx.return_value = (mock_ctx, None)

        mock_store = Mock()
        mock_store.lead_list.return_value = mock_leads
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["research", "lead", "enrich", "74", "--dry-run"])
        output = strip_ansi(result.output)

        # Should show leads that would be enriched
        assert "dry" in output.lower() or "would" in output.lower()
        # Should not call FallbackProvider or update leads
        mock_store.lead_update.assert_not_called()


class TestLeadEnrichExecution:
    """Tests for actual enrichment execution."""

    @patch("erdos.commands.research.lead.get_app_context")
    @patch("erdos.commands.research.lead.FSResearchStore")
    @patch("erdos.commands.research.lead.LeadEnrichmentService")
    def test_enrich_calls_service(
        self,
        mock_service_cls: Mock,
        mock_store_cls: Mock,
        mock_get_ctx: Mock,
        mock_leads: list[LeadRecord],
        strip_ansi: Callable[[str], str],
    ) -> None:
        """Command should use LeadEnrichmentService."""
        from datetime import UTC, datetime

        # Setup mocks
        mock_ctx = Mock()
        mock_ctx.problems.get.return_value = Mock(id=74, title="Test Problem")
        mock_get_ctx.return_value = (mock_ctx, None)

        mock_store = Mock()
        mock_store.lead_list.return_value = mock_leads
        mock_store_cls.return_value = mock_store

        # Mock enrichment results
        now = datetime.now(UTC)
        enriched_lead = mock_leads[0].model_copy(
            update={
                "enriched_title": "Enriched Title",
                "enriched_at": now,
            }
        )
        mock_service = Mock()
        mock_service.enrich_leads.return_value = (
            [EnrichmentResult(lead=enriched_lead, provider="openalex")],
            EnrichmentStats(total=2, with_identifiers=2, enriched=1),
        )
        mock_service_cls.return_value = mock_service

        result = runner.invoke(app, ["research", "lead", "enrich", "74"])
        output = strip_ansi(result.output)

        # Should call enrichment service
        mock_service.enrich_leads.assert_called_once()
        # Should report results
        assert "enrich" in output.lower()
