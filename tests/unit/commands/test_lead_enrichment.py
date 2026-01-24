"""Tests for lead add enrichment flags (SPEC-030, SPEC-031)."""

from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from erdos.cli import app
from tests.cli_runner import make_cli_runner


@pytest.fixture
def runner() -> CliRunner:
    return make_cli_runner()


def test_lead_add_help_shows_fetch_citations(
    runner: CliRunner, strip_ansi: Callable[[str], str]
) -> None:
    """Verify lead add help shows --fetch-citations flag."""
    result = runner.invoke(app, ["research", "lead", "add", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--fetch-citations" in output
    assert "Semantic Scholar" in output


def test_lead_add_help_shows_fetch_msc(
    runner: CliRunner, strip_ansi: Callable[[str], str]
) -> None:
    """Verify lead add help shows --fetch-msc flag."""
    result = runner.invoke(app, ["research", "lead", "add", "--help"])
    output = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--fetch-msc" in output
    assert "zbMATH" in output
