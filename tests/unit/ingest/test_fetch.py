"""Unit tests for ingest fetch coordination helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from erdos.core.ingest.config import FetchConfig, IngestConfig, PDFConfig
from erdos.core.ingest.fetch import (
    MetadataSource,
    build_provider_from_source,
    process_all_references,
)
from erdos.core.ingest.models import PDFDownloadResult
from erdos.core.models import ProblemRecord, ProblemStatus, ReferenceEntry
from erdos.core.providers.fallback import FallbackProvider
from erdos.core.providers.openalex import OpenAlexProvider


DEFAULT_TIMEOUT = 30.0
DEFAULT_MAILTO = "test@example.com"
DEFAULT_DELAY = 0.0


def test_build_provider_openalex_respects_mailto_and_timeout() -> None:
    provider = build_provider_from_source(
        MetadataSource.OPENALEX,
        mailto="cli@example.com",
        timeout=12.5,
    )

    assert isinstance(provider, FallbackProvider)
    openalex = provider.doi_chain[0]
    assert isinstance(openalex, OpenAlexProvider)
    assert openalex.client_config.email == "cli@example.com"
    assert openalex.client_config.timeout == 12.5


class TestProcessAllReferencesUrlOnly:
    """Tests for URL-only PDF reference handling (BUG-055)."""

    def test_process_all_references_handles_url_only_pdf(self, tmp_path: Path) -> None:
        """URL-only references pointing to PDFs are processed when pdf.enabled."""
        # Create a problem with a URL-only PDF reference
        problem = ProblemRecord(
            id=99,
            title="Test Problem",
            statement="Test statement",
            status=ProblemStatus.OPEN,
            references=[
                ReferenceEntry(
                    key="TestPaper2023",
                    citation="Test Paper (2023)",
                    url="https://example.com/paper.pdf",
                )
            ],
        )

        # Mock the PDF download
        mock_result = PDFDownloadResult(
            cache_path=Path("literature/cache/pdf/TestPaper2023/paper.pdf"),
            cache_hash="abc123",
            extracted=True,
            extract_path=Path("literature/extracts/pdf/TestPaper2023/fulltext.md"),
            error=None,
        )

        config = IngestConfig(
            fetch=FetchConfig(
                allow_network=True,
                allow_download=True,
                repo_root=tmp_path,
                timeout=DEFAULT_TIMEOUT,
                mailto=DEFAULT_MAILTO,
                delay=DEFAULT_DELAY,
            ),
            pdf=PDFConfig(enabled=True),
        )

        with patch(
            "erdos.core.ingest.fetch.download_and_extract_pdf",
            return_value=mock_result,
        ) as mock_download:
            result = process_all_references(
                problem, existing_manifest=None, config=config
            )

            # The URL-only PDF should be processed
            assert result.skipped == 0
            assert result.failed == 0
            assert len(result.entries) == 1
            assert result.entries[0].reference.source == "pdf-url"
            assert result.entries[0].cached is True
            mock_download.assert_called_once()

    def test_process_all_references_skips_url_only_non_pdf(
        self, tmp_path: Path
    ) -> None:
        """URL-only references NOT pointing to PDFs are skipped."""
        # Create a problem with a URL-only HTML reference
        problem = ProblemRecord(
            id=99,
            title="Test Problem",
            statement="Test statement",
            status=ProblemStatus.OPEN,
            references=[
                ReferenceEntry(
                    key="TestPage2023",
                    citation="Test Page (2023)",
                    url="https://example.com/page.html",
                )
            ],
        )

        config = IngestConfig(
            fetch=FetchConfig(
                allow_network=True,
                allow_download=True,
                repo_root=tmp_path,
                timeout=DEFAULT_TIMEOUT,
                mailto=DEFAULT_MAILTO,
                delay=DEFAULT_DELAY,
            ),
            pdf=PDFConfig(enabled=True),
        )

        result = process_all_references(problem, existing_manifest=None, config=config)

        # The URL-only HTML reference should be skipped
        assert result.skipped == 1
        assert result.failed == 0
        assert len(result.entries) == 0

    def test_process_all_references_skips_url_only_pdf_when_pdf_disabled(
        self, tmp_path: Path
    ) -> None:
        """URL-only PDF references are skipped when pdf.enabled=False."""
        problem = ProblemRecord(
            id=99,
            title="Test Problem",
            statement="Test statement",
            status=ProblemStatus.OPEN,
            references=[
                ReferenceEntry(
                    key="TestPaper2023",
                    url="https://example.com/paper.pdf",
                )
            ],
        )

        config = IngestConfig(
            fetch=FetchConfig(
                allow_network=True,
                allow_download=True,
                repo_root=tmp_path,
                timeout=DEFAULT_TIMEOUT,
                mailto=DEFAULT_MAILTO,
                delay=DEFAULT_DELAY,
            ),
            pdf=PDFConfig(enabled=False),
        )

        result = process_all_references(problem, existing_manifest=None, config=config)

        # Should be skipped because PDF is disabled
        assert result.skipped == 1
        assert len(result.entries) == 0
