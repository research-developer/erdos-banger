"""Tests for lead add enrichment flags (SPEC-030, SPEC-031)."""

from collections.abc import Callable

from typer.testing import CliRunner

from erdos.cli import app


runner = CliRunner()


def test_lead_add_help_shows_fetch_citations(strip_ansi: Callable[[str], str]) -> None:
    """Verify lead add help shows --fetch-citations flag."""
    result = runner.invoke(app, ["research", "lead", "add", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--fetch-citations" in output
    assert "Semantic Scholar" in output


def test_lead_add_help_shows_fetch_msc(strip_ansi: Callable[[str], str]) -> None:
    """Verify lead add help shows --fetch-msc flag."""
    result = runner.invoke(app, ["research", "lead", "add", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--fetch-msc" in output
    assert "zbMATH" in output
