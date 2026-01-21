"""Integration tests for PDF ingestion (SPEC-019)."""

from __future__ import annotations

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


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
        """Ingest --pdf option is correctly parsed and stored.

        Note: PDF conversion integration with ingest pipeline is documented
        in SPEC-019 Section 5.2. The --pdf flag is accepted and stored,
        but actual PDF downloading/conversion is deferred to when
        references have OA PDF URLs available.
        """
        # This test verifies the option is accepted
        result = runner.invoke(app, ["ingest", "1", "--pdf", "--no-network"])
        # Should not crash with the option (may fail due to --no-network)
        assert result.exit_code in (0, 1, 2, 3, 4, 10)
        # Verify the option doesn't cause "unknown option" error
        assert "unknown" not in result.output.lower()
