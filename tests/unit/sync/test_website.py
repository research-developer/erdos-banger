"""Tests for website data extraction (SPEC-035)."""

from __future__ import annotations

from pathlib import Path

import pytest

from erdos.core.sync.website import (
    _extract_content,
    _extract_latex_source_url,
    _extract_references,
    _extract_status_badge,
    _extract_tags,
    _extract_title_from_html,
    parse_problem_html,
    save_latex_source,
)


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "website"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def html_problem_6_proved() -> str:
    """HTML fixture for problem #6 (PROVED status)."""
    return load_fixture("problem_6_proved.html")


@pytest.fixture
def html_problem_1_open() -> str:
    """HTML fixture for problem #1 (OPEN status)."""
    return load_fixture("problem_1_open.html")


@pytest.fixture
def html_problem_minimal() -> str:
    """HTML fixture for a minimal problem page."""
    return load_fixture("problem_minimal.html")


@pytest.fixture
def html_problem_no_content() -> str:
    """HTML fixture for a problem without content div."""
    return load_fixture("problem_no_content.html")


# =============================================================================
# Content extraction tests
# =============================================================================


class TestExtractContent:
    """Tests for _extract_content."""

    def test_extract_from_proved_problem(self, html_problem_6_proved: str) -> None:
        content = _extract_content(html_problem_6_proved)
        assert content is not None
        assert "d_n=p_{n+1}-p_n" in content
        assert "infinitely many" in content

    def test_extract_from_open_problem(self, html_problem_1_open: str) -> None:
        content = _extract_content(html_problem_1_open)
        assert content is not None
        assert "subset sums" in content

    def test_extract_from_minimal(self, html_problem_minimal: str) -> None:
        content = _extract_content(html_problem_minimal)
        assert content == "A minimal problem statement for testing."

    def test_extract_returns_none_when_missing(
        self, html_problem_no_content: str
    ) -> None:
        content = _extract_content(html_problem_no_content)
        assert content is None

    def test_html_entities_decoded(self) -> None:
        """HTML entities like &#60; are decoded to <."""
        html = '<div id="content">$a &#60; b$</div>'
        content = _extract_content(html)
        assert content == "$a < b$"


class TestExtractTitle:
    """Tests for _extract_title_from_html."""

    def test_extract_from_title_tag(self, html_problem_6_proved: str) -> None:
        title = _extract_title_from_html(html_problem_6_proved, 6)
        assert "Erdős Problem #6" in title or "6" in title

    def test_fallback_to_default(self) -> None:
        title = _extract_title_from_html("<html></html>", 42)
        assert title == "Erdős Problem #42"

    def test_html_entities_in_title(self) -> None:
        html = "<title>Erd&#337;s Problem #1</title>"
        title = _extract_title_from_html(html, 1)
        assert "Erdős" in title or "Erdos" in title or "1" in title


class TestExtractStatusBadge:
    """Tests for _extract_status_badge."""

    def test_extract_proved(self, html_problem_6_proved: str) -> None:
        status = _extract_status_badge(html_problem_6_proved)
        assert status == "PROVED"

    def test_extract_open(self, html_problem_1_open: str) -> None:
        status = _extract_status_badge(html_problem_1_open)
        assert status == "OPEN"

    def test_returns_none_when_missing(self) -> None:
        html = "<html><body></body></html>"
        status = _extract_status_badge(html)
        assert status is None


class TestExtractTags:
    """Tests for _extract_tags."""

    def test_extract_multiple_tags(self, html_problem_6_proved: str) -> None:
        tags = _extract_tags(html_problem_6_proved)
        assert "number theory" in tags
        assert "primes" in tags
        assert len(tags) == 2

    def test_extract_different_tags(self, html_problem_1_open: str) -> None:
        tags = _extract_tags(html_problem_1_open)
        assert "number theory" in tags
        assert "additive combinatorics" in tags

    def test_returns_empty_when_missing(self, html_problem_minimal: str) -> None:
        tags = _extract_tags(html_problem_minimal)
        assert tags == []


class TestExtractReferences:
    """Tests for _extract_references."""

    def test_extract_multiple_refs(self, html_problem_6_proved: str) -> None:
        refs = _extract_references(html_problem_6_proved)
        keys = [r.key for r in refs]
        assert "Er55c" in keys
        assert "Er57" in keys
        assert "ErGr80" in keys

    def test_refs_are_unique(self, html_problem_1_open: str) -> None:
        """Duplicate citation keys should be deduplicated."""
        refs = _extract_references(html_problem_1_open)
        keys = [r.key for r in refs]
        # Should have unique keys only
        assert len(keys) == len(set(keys))

    def test_returns_empty_when_missing(self, html_problem_no_content: str) -> None:
        refs = _extract_references(html_problem_no_content)
        assert len(refs) == 0

    def test_page_refs_normalized(self) -> None:
        """Page references like [Er65,p.123] should normalize to Er65."""
        html = '<div id="problem_id">[Er65,p.123]</div>'
        refs = _extract_references(html)
        assert len(refs) == 1
        assert refs[0].key == "Er65"


class TestExtractLatexUrl:
    """Tests for _extract_latex_source_url."""

    def test_extract_latex_url(self, html_problem_6_proved: str) -> None:
        url = _extract_latex_source_url(html_problem_6_proved, 6)
        assert url is not None
        assert "latex/6" in url

    def test_fallback_when_link_missing(self) -> None:
        html = '<a href="/latex/42">source</a>'
        url = _extract_latex_source_url(html, 42)
        # Should find /latex/42 in content
        assert url is not None
        assert "42" in url


# =============================================================================
# Parse integration tests
# =============================================================================


class TestParseProblemHtml:
    """Integration tests for parse_problem_html."""

    def test_parse_proved_problem(self, html_problem_6_proved: str) -> None:
        data = parse_problem_html(html_problem_6_proved, 6)

        assert data.problem_id == 6
        assert data.title is not None
        assert "Erdős" in data.title or "Problem" in data.title
        assert data.statement is not None
        assert "d_n" in data.statement
        assert data.status_badge_text == "PROVED"
        assert "number theory" in data.tags
        assert "primes" in data.tags
        assert len(data.references) >= 2

    def test_parse_open_problem(self, html_problem_1_open: str) -> None:
        data = parse_problem_html(html_problem_1_open, 1)

        assert data.problem_id == 1
        assert data.status_badge_text == "OPEN"
        assert data.statement is not None
        assert "subset sums" in data.statement
        assert "additive combinatorics" in data.tags

    def test_parse_minimal_problem(self, html_problem_minimal: str) -> None:
        data = parse_problem_html(html_problem_minimal, 99)

        assert data.problem_id == 99
        assert data.statement is not None
        assert data.statement == "A minimal problem statement for testing."
        assert data.tags == []
        assert data.references == []

    def test_parse_problem_without_content(self, html_problem_no_content: str) -> None:
        data = parse_problem_html(html_problem_no_content, 404)

        assert data.problem_id == 404
        assert data.statement is None  # No content div
        assert data.title is not None  # Should have fallback title


# =============================================================================
# LaTeX source tests
# =============================================================================


class TestSaveLatexSource:
    """Tests for save_latex_source."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        latex = r"\section{Problem 6} Let $d_n = p_{n+1} - p_n$."
        path = save_latex_source(6, latex, output_dir=tmp_path)

        assert path.exists()
        assert path.name == "6.tex"
        assert path.read_text(encoding="utf-8") == latex

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "nested" / "latex"
        latex = "test content"
        path = save_latex_source(1, latex, output_dir=output_dir)

        assert path.exists()
        assert output_dir.exists()

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        latex1 = "first version"
        latex2 = "second version"

        save_latex_source(1, latex1, output_dir=tmp_path)
        path = save_latex_source(1, latex2, output_dir=tmp_path)

        assert path.read_text(encoding="utf-8") == latex2
