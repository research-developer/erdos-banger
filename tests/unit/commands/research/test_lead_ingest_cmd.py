"""Tests for `erdos research lead ingest` command (SPEC-036).

TDD Phase 5: CLI command for lead ingestion into manifest.
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


class TestLeadIngestHelp:
    """Tests for command help and basic invocation."""

    def test_ingest_help_shows_usage(self, strip_ansi: Callable[[str], str]) -> None:
        """--help should show command usage."""
        result = runner.invoke(app, ["research", "lead", "ingest", "--help"])
        output = strip_ansi(result.output)
        assert "ingest" in output.lower()
        assert "--dry-run" in output

    def test_ingest_requires_problem_id(self, strip_ansi: Callable[[str], str]) -> None:
        """Command should require problem_id argument."""
        result = runner.invoke(app, ["research", "lead", "ingest"])
        output = strip_ansi(result.output)
        # Should show missing argument error
        assert result.exit_code != 0


class TestLeadIngestDryRun:
    """Tests for --dry-run mode."""

    @patch("erdos.core.ingest.service._load_existing_manifest")
    @patch("erdos.commands.research.lead.get_app_context")
    @patch("erdos.commands.research.lead.FSResearchStore")
    def test_ingest_dry_run_shows_preview(
        self,
        mock_store_cls: Mock,
        mock_get_ctx: Mock,
        mock_load_manifest: Mock,
        strip_ansi: Callable[[str], str],
        tmp_path,
    ) -> None:
        """--dry-run should show what would be ingested."""
        from datetime import UTC, datetime

        from erdos.core.models import ProblemManifest
        from erdos.core.research.models import LeadRecord, LeadSource

        # Setup mocks
        mock_ctx = Mock()
        mock_ctx.problems.get.return_value = Mock(id=74, title="Test Problem")
        mock_ctx.config.repo_root = tmp_path
        mock_get_ctx.return_value = (mock_ctx, None)

        # Mock manifest loading
        mock_load_manifest.return_value = ProblemManifest(problem_id=74, entries=[])

        now = datetime.now(UTC)
        mock_leads = [
            LeadRecord(
                problem_id=74,
                id="lead_001",
                title="Enriched Lead",
                source=LeadSource(doi="10.1234/test"),
                tags=[],
                created_at=now,
                updated_at=now,
                enriched_at=now,  # Enriched
                enriched_title="Full Title",
            ),
        ]

        mock_store = Mock()
        mock_store.lead_list.return_value = mock_leads
        mock_store_cls.return_value = mock_store

        result = runner.invoke(app, ["research", "lead", "ingest", "74", "--dry-run"])
        output = strip_ansi(result.output)

        # Should show preview
        assert "would" in output.lower() or "add" in output.lower()
