"""Integration tests for PDF ingestion (SPEC-019)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import responses

from erdos.cli import app
from erdos.core.literature_paths import (
    get_pdf_cache_path,
    get_pdf_extract_path,
    sanitize_reference_id,
)
from tests.cli_runner import make_cli_runner


runner = make_cli_runner()


def _data_dir(tmp_path: Path, sample_problems_yaml: Path) -> Path:
    """Create a data directory with sample problems."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(sample_problems_yaml, data_dir / "problems.yaml")
    return data_dir


class TestIngestPDFOptions:
    """Tests for ingest command PDF options."""

    def test_ingest_help_shows_pdf_options(self, strip_ansi) -> None:
        """Ingest --help shows PDF-related options."""
        result = runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        # Check PDF options are documented
        assert "--pdf" in output or "--no-pdf" in output

    def test_ingest_pdf_flag_accepted(self) -> None:
        """Ingest --pdf flag is accepted."""
        result = runner.invoke(app, ["ingest", "1", "--pdf", "--no-network"])
        # Should not fail with "unknown option"
        assert "unknown option" not in result.output.lower()
        # May fail for other reasons (no network, etc.)
        assert result.exit_code in (0, 1, 2, 3, 4, 10)

    def test_ingest_no_pdf_flag_accepted(self) -> None:
        """Ingest --no-pdf flag is accepted."""
        result = runner.invoke(app, ["ingest", "1", "--no-pdf", "--no-network"])
        # Should not fail with "unknown option"
        assert "unknown option" not in result.output.lower()
        assert result.exit_code in (0, 1, 2, 3, 4, 10)

    def test_ingest_pdf_converter_option(self) -> None:
        """Ingest --pdf-converter option is accepted."""
        result = runner.invoke(
            app,
            ["ingest", "1", "--pdf", "--pdf-converter", "pdfplumber", "--no-network"],
        )
        assert "unknown option" not in result.output.lower()
        assert result.exit_code in (0, 1, 2, 3, 4, 10)

    def test_ingest_use_llm_option(self) -> None:
        """Ingest --use-llm option is accepted."""
        result = runner.invoke(
            app, ["ingest", "1", "--pdf", "--use-llm", "--no-network"]
        )
        assert "unknown option" not in result.output.lower()
        assert result.exit_code in (0, 1, 2, 3, 4, 10)


class TestIngestPDFBehavior:
    """Tests for ingest command PDF behavior."""

    def test_ingest_with_pdf_option_is_stored(self) -> None:
        """Ingest --pdf option is accepted (CLI wiring)."""
        # This test verifies the option is accepted
        result = runner.invoke(app, ["ingest", "1", "--pdf", "--no-network"])
        # Should not crash with the option (may fail due to --no-network)
        assert result.exit_code in (0, 1, 2, 3, 4, 10)
        # Verify the option doesn't cause "unknown option" error
        assert "unknown" not in result.output.lower()

    @responses.activate
    def test_ingest_pdf_download_and_extract(
        self,
        monkeypatch,
        tmp_path: Path,
        sample_problems_yaml: Path,
    ) -> None:
        """Ingest --pdf downloads + converts PDFs when `pdf_url` exists (BUG-022)."""
        from erdos.core.pdf.converter import PDFConversionResult

        # Problem 316 in sample fixture has a DOI-only reference.
        doi = "10.4007/annals.2015.181.1.6"
        pdf_url = "https://example.com/paper.pdf"

        # Mock OpenAlex DOI lookup (ingest uses OpenAlex by default when --source openalex).
        responses.add(
            responses.GET,
            f"https://api.openalex.org/works/https://doi.org/{doi}",
            json={
                "id": "https://openalex.org/W123",
                "title": "Test PDF paper",
                "doi": f"https://doi.org/{doi}",
                "publication_year": 2015,
                "open_access": {"oa_status": "gold"},
                "primary_location": {
                    "pdf_url": pdf_url,
                    "source": {"display_name": ""},
                },
                "authorships": [],
                "concepts": [],
            },
            status=200,
        )

        # Mock PDF download.
        responses.add(
            responses.GET,
            pdf_url,
            body=b"%PDF-1.4 test content",
            status=200,
            content_type="application/pdf",
        )

        # Patch convert_pdf to avoid optional dependencies (marker/pdfplumber).
        captured: dict[str, object] = {}

        def fake_convert_pdf(_pdf_path: Path, config) -> PDFConversionResult:
            captured["converter"] = getattr(config, "converter", None)
            captured["use_llm"] = getattr(config, "use_llm", None)
            return PDFConversionResult(
                success=True,
                text="converted pdf text",
                converter=str(getattr(config, "converter", "unknown")),
            )

        import erdos.core.ingest.pdf_download as pdf_download_module

        monkeypatch.setattr(pdf_download_module, "convert_pdf", fake_convert_pdf)

        # Setup isolated environment.
        data_dir = _data_dir(tmp_path, sample_problems_yaml)
        repo_root = tmp_path

        result = runner.invoke(
            app,
            [
                "--json",
                "ingest",
                "316",
                "--source",
                "openalex",
                "--pdf",
                "--pdf-converter",
                "pdfplumber",
                "--use-llm",
                "--delay",
                "0",
            ],
            env={
                "ERDOS_DATA_PATH": str(data_dir),
                "ERDOS_REPO_ROOT": str(repo_root),
            },
        )
        assert result.exit_code == 0, result.stdout

        data = json.loads(result.stdout)
        assert data["success"] is True

        reference_id = sanitize_reference_id(f"doi:{doi.lower()}")
        cache_path = repo_root / get_pdf_cache_path(reference_id)
        extract_path = repo_root / get_pdf_extract_path(reference_id)

        assert cache_path.exists()
        assert extract_path.exists()
        assert extract_path.read_text(encoding="utf-8") == "converted pdf text"
        assert captured["converter"] == "pdfplumber"
        assert captured["use_llm"] is True
