"""Tests for forum proof-link extraction (SPEC-035)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erdos.core.sync.forum import (
    extract_proof_links_from_html,
    parse_forum_html,
    save_proof_links_cache,
)
from erdos.core.sync.models import ProofLink, ProofLinksCache


# =============================================================================
# Fixtures
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "sync" / "forum"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def html_thread_with_github() -> str:
    """Forum thread with a GitHub proof link."""
    return load_fixture("thread_347_with_github_link.html")


@pytest.fixture
def html_thread_multiple_links() -> str:
    """Forum thread with multiple GitHub and GitLab links."""
    return load_fixture("thread_with_multiple_links.html")


@pytest.fixture
def html_thread_no_links() -> str:
    """Forum thread with no proof links (only arxiv)."""
    return load_fixture("thread_no_links.html")


@pytest.fixture
def html_thread_empty() -> str:
    """Empty forum thread."""
    return load_fixture("thread_empty.html")


# =============================================================================
# Link extraction tests
# =============================================================================


class TestExtractProofLinksFromHtml:
    """Tests for extract_proof_links_from_html (pure parsing)."""

    def test_extract_github_link(self, html_thread_with_github: str) -> None:
        """Extract a single GitHub link from forum HTML."""
        links = extract_proof_links_from_html(html_thread_with_github, problem_id=347)
        assert len(links) == 1
        assert links[0].url == "https://github.com/mathprover123/erdos-347-proof"

    def test_extract_author_from_post(self, html_thread_with_github: str) -> None:
        """Extract author username from post context."""
        links = extract_proof_links_from_html(html_thread_with_github, problem_id=347)
        assert len(links) == 1
        assert links[0].author == "mathprover123"

    def test_extract_lean_version_hint(self, html_thread_with_github: str) -> None:
        """Extract Lean version hint from surrounding text."""
        links = extract_proof_links_from_html(html_thread_with_github, problem_id=347)
        assert len(links) == 1
        assert links[0].lean_version_hint is not None
        assert "4.3.0" in links[0].lean_version_hint

    def test_extract_multiple_links(self, html_thread_multiple_links: str) -> None:
        """Extract multiple GitHub/GitLab links from thread."""
        links = extract_proof_links_from_html(
            html_thread_multiple_links, problem_id=100
        )
        assert len(links) == 3
        urls = [link.url for link in links]
        assert "https://github.com/first_prover/erdos-100-attempt" in urls
        assert "https://gitlab.com/second_prover/erdos-problem-100" in urls
        assert "https://github.com/third_contributor/erdos-proofs" in urls

    def test_links_in_order(self, html_thread_multiple_links: str) -> None:
        """Links are extracted in document order (deterministic)."""
        links = extract_proof_links_from_html(
            html_thread_multiple_links, problem_id=100
        )
        # First link should be from first_prover (appears first in HTML)
        assert links[0].url == "https://github.com/first_prover/erdos-100-attempt"

    def test_no_proof_links(self, html_thread_no_links: str) -> None:
        """Return empty list when no GitHub/GitLab links found."""
        links = extract_proof_links_from_html(html_thread_no_links, problem_id=50)
        assert len(links) == 0

    def test_ignores_non_code_links(self, html_thread_no_links: str) -> None:
        """Ignore non-code links like arxiv."""
        links = extract_proof_links_from_html(html_thread_no_links, problem_id=50)
        # Should not include the arxiv link
        assert len(links) == 0

    def test_empty_thread(self, html_thread_empty: str) -> None:
        """Handle empty thread gracefully."""
        links = extract_proof_links_from_html(html_thread_empty, problem_id=999)
        assert len(links) == 0


class TestExtractLeanVersionHint:
    """Tests for Lean version hint extraction."""

    def test_lean_4_version(self) -> None:
        """Extract Lean 4.x.y version."""
        html = """
        <div class="post">
            <div class="author">user</div>
            <div class="post-content">
                <p>Proof: <a href="https://github.com/user/repo">repo</a></p>
                <p>Requires Lean 4.4.0</p>
            </div>
        </div>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].lean_version_hint == "Lean 4.4.0"

    def test_lean_toolchain_version(self) -> None:
        """Extract leanprover/lean4:v4.x.y format."""
        html = """
        <div class="post">
            <div class="author">user</div>
            <div class="post-content">
                <p><a href="https://github.com/user/repo">repo</a></p>
                <p>Uses leanprover/lean4:v4.3.0</p>
            </div>
        </div>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert "4.3.0" in (links[0].lean_version_hint or "")

    def test_no_version_hint(self) -> None:
        """Return None when no version mentioned."""
        html = """
        <div class="post">
            <div class="author">user</div>
            <div class="post-content">
                <p>Check out <a href="https://github.com/user/repo">my proof</a></p>
            </div>
        </div>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].lean_version_hint is None


class TestExtractUrlPatterns:
    """Tests for URL pattern matching."""

    def test_github_standard_url(self) -> None:
        """Match standard GitHub repo URL."""
        html = '<a href="https://github.com/user/repo">link</a>'
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].url == "https://github.com/user/repo"

    def test_github_with_path(self) -> None:
        """Match GitHub URL with path (include full URL)."""
        html = '<a href="https://github.com/user/repo/tree/main">link</a>'
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].url == "https://github.com/user/repo/tree/main"

    def test_gitlab_url(self) -> None:
        """Match GitLab repo URL."""
        html = '<a href="https://gitlab.com/user/project">link</a>'
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].url == "https://gitlab.com/user/project"

    def test_url_in_text(self) -> None:
        """Match GitHub URL as plain text (not in anchor)."""
        html = """
        <div class="post-content">
            <p>See https://github.com/user/proof-repo for the proof.</p>
        </div>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1
        assert links[0].url == "https://github.com/user/proof-repo"

    def test_ignores_github_issues(self) -> None:
        """Ignore GitHub issues/PRs, only repos."""
        html = """
        <a href="https://github.com/user/repo/issues/123">issue</a>
        <a href="https://github.com/user/repo/pull/456">PR</a>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        # Issues and PRs should be filtered out
        assert len(links) == 0

    def test_ignores_http_urls(self) -> None:
        """Only accept https:// URLs for security."""
        html = '<a href="http://github.com/user/repo">insecure</a>'
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 0

    def test_deduplicates_urls(self) -> None:
        """Same URL mentioned multiple times is extracted once."""
        html = """
        <a href="https://github.com/user/repo">first mention</a>
        <p>Check https://github.com/user/repo again.</p>
        """
        links = extract_proof_links_from_html(html, problem_id=1)
        assert len(links) == 1


# =============================================================================
# Parse forum HTML tests
# =============================================================================


class TestParseForumHtml:
    """Tests for parse_forum_html (returns ProofLinksCache)."""

    def test_parse_returns_cache_model(self, html_thread_with_github: str) -> None:
        """parse_forum_html returns a ProofLinksCache."""
        cache = parse_forum_html(
            html_thread_with_github,
            problem_id=347,
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
        )
        assert isinstance(cache, ProofLinksCache)
        assert cache.problem_id == 347
        assert len(cache.links) == 1
        assert (
            cache.forum_thread_url == "https://www.erdosproblems.com/forum/thread/347"
        )

    def test_parse_empty_thread(self, html_thread_empty: str) -> None:
        """Parse empty thread returns cache with no links."""
        cache = parse_forum_html(
            html_thread_empty,
            problem_id=999,
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
        )
        assert cache.problem_id == 999
        assert len(cache.links) == 0

    def test_parse_sets_extracted_at(self, html_thread_with_github: str) -> None:
        """extracted_at is set correctly."""
        now = datetime(2026, 1, 24, 15, 30, 0, tzinfo=UTC)
        cache = parse_forum_html(
            html_thread_with_github, problem_id=347, extracted_at=now
        )
        assert cache.extracted_at == now


# =============================================================================
# Save proof links cache tests
# =============================================================================


class TestSaveProofLinksCache:
    """Tests for save_proof_links_cache."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Saving cache creates links.json file."""
        cache = ProofLinksCache(
            problem_id=347,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/347",
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
            links=[
                ProofLink(
                    url="https://github.com/user/proof",
                    author="testuser",
                    lean_version_hint="Lean 4.3.0",
                ),
            ],
        )
        path = save_proof_links_cache(cache, cache_dir=tmp_path)

        assert path.exists()
        assert path.name == "links.json"
        assert path.parent.name == "347"

    def test_save_creates_directory_structure(self, tmp_path: Path) -> None:
        """Creates proofs/<id>/ directory structure."""
        cache = ProofLinksCache(
            problem_id=100,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/100",
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
            links=[],
        )
        path = save_proof_links_cache(cache, cache_dir=tmp_path)

        expected_dir = tmp_path / "100"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_save_json_is_valid(self, tmp_path: Path) -> None:
        """Saved JSON can be loaded and matches original."""
        import json

        cache = ProofLinksCache(
            problem_id=42,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/42",
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
            links=[
                ProofLink(url="https://github.com/a/b"),
                ProofLink(url="https://gitlab.com/c/d", author="user"),
            ],
        )
        path = save_proof_links_cache(cache, cache_dir=tmp_path)

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["problem_id"] == 42
        assert len(data["links"]) == 2
        assert data["links"][0]["url"] == "https://github.com/a/b"

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        """Saving again overwrites the existing file."""
        cache1 = ProofLinksCache(
            problem_id=1,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/1",
            extracted_at=datetime(2026, 1, 24, 10, 0, 0, tzinfo=UTC),
            links=[ProofLink(url="https://github.com/old/repo")],
        )
        cache2 = ProofLinksCache(
            problem_id=1,
            forum_thread_url="https://www.erdosproblems.com/forum/thread/1",
            extracted_at=datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC),
            links=[ProofLink(url="https://github.com/new/repo")],
        )

        save_proof_links_cache(cache1, cache_dir=tmp_path)
        path = save_proof_links_cache(cache2, cache_dir=tmp_path)

        import json

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        assert data["links"][0]["url"] == "https://github.com/new/repo"
