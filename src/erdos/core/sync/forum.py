"""Forum proof-link extraction for erdosproblems.com (SPEC-035).

This module extracts GitHub/GitLab repository links from forum threads.
It does NOT scrape arbitrary content - only structured repository URLs.

URL pattern: https://www.erdosproblems.com/forum/thread/{problem_id}
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from erdos.core.sync.models import ProofLink, ProofLinksCache


logger = logging.getLogger(__name__)


# Rate limiting: Be polite to T. F. Bloom's server
FORUM_RATE_LIMIT = 2.0  # seconds between requests
_rate_limit_state: dict[str, float] = {"last_request_time": 0.0}

# Allowed repository hosts (security: only https, allowlist)
ALLOWED_HOSTS = frozenset({"github.com", "gitlab.com"})

# Patterns to filter out (not actual proof repos)
EXCLUDED_PATHS = frozenset(
    {
        "/issues/",
        "/pull/",
        "/discussions/",
        "/wiki/",
        "/blob/",
        "/releases/",
        "/actions/",
        "/commit/",
        "/commits/",
    }
)


class ForumFetchError(Exception):
    """Raised when forum fetch fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ForumFetchResult:
    """Result of fetching a forum thread."""

    problem_id: int
    html_content: str
    http_status: int
    fetched_at: datetime


def _rate_limit() -> None:
    """Enforce rate limiting between requests."""
    now = time.monotonic()
    elapsed = now - _rate_limit_state["last_request_time"]
    if elapsed < FORUM_RATE_LIMIT:
        time.sleep(FORUM_RATE_LIMIT - elapsed)
    _rate_limit_state["last_request_time"] = time.monotonic()


def _is_valid_repo_url(url: str) -> bool:
    """Check if URL is a valid repository URL (https, allowed host, not excluded)."""
    if not url.startswith("https://"):
        return False

    # Check against allowed hosts
    for host in ALLOWED_HOSTS:
        if f"https://{host}/" in url:
            # Check not in excluded paths
            return all(excluded not in url for excluded in EXCLUDED_PATHS)

    return False


def _normalize_repo_url(url: str) -> str:
    """Normalize repository URL (strip trailing slashes, etc)."""
    # Remove trailing slash
    url = url.rstrip("/")
    # Remove .git suffix if present
    if url.endswith(".git"):
        url = url[:-4]
    return url


def _extract_author_from_context(html_context: str) -> str | None:
    """Extract author username from surrounding HTML context."""
    # Try to find author in common patterns
    patterns = [
        r'class="author"[^>]*>([^<]+)</span>',
        r'<span\s+class="author">([^<]+)</span>',
        r'class="author">([^<]+)<',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_context, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_lean_version_from_context(html_context: str) -> str | None:
    """Extract Lean version hint from surrounding text."""
    # Try various Lean version patterns
    patterns = [
        r"(Lean\s+4\.\d+\.\d+)",  # Lean 4.3.0
        r"(leanprover/lean4:v\d+\.\d+\.\d+)",  # leanprover/lean4:v4.3.0
        r"(Lean\s+4\.\d+)",  # Lean 4.3
    ]
    for pattern in patterns:
        match = re.search(pattern, html_context, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_proof_links_from_html(
    html_text: str,
    problem_id: int,  # noqa: ARG001
) -> list[ProofLink]:
    """
    Extract GitHub/GitLab proof repository links from forum HTML.

    This is a pure function suitable for offline testing with fixtures.

    Strategy:
    1. Find all URLs matching allowed hosts (github.com, gitlab.com)
    2. Filter out non-repo links (issues, PRs, blobs, etc.)
    3. For each valid link, extract context (author, Lean version)
    4. Return deduplicated list in document order

    Args:
        html_text: Raw HTML content of forum thread
        problem_id: Problem ID for context

    Returns:
        List of ProofLink objects with extracted metadata
    """
    links: list[ProofLink] = []
    seen_urls: set[str] = set()

    # Find all URLs - both in href attributes and plain text
    # Pattern matches https://github.com/... and https://gitlab.com/...
    url_pattern = r'https://(?:github\.com|gitlab\.com)/[^\s"<>\)\']+(?<![.,;:\)\]\}])'

    for match in re.finditer(url_pattern, html_text):
        raw_url = match.group(0)
        url = _normalize_repo_url(raw_url)

        # Skip if not valid or already seen
        if not _is_valid_repo_url(url) or url in seen_urls:
            continue

        seen_urls.add(url)

        # Get surrounding context (500 chars before and 200 chars after the match)
        start_pos = max(0, match.start() - 500)
        end_pos = min(len(html_text), match.end() + 200)
        context = html_text[start_pos:end_pos]

        # Extract metadata from context
        author = _extract_author_from_context(context)
        lean_version = _extract_lean_version_from_context(context)

        links.append(
            ProofLink(
                url=url,
                author=author,
                lean_version_hint=lean_version,
            )
        )

    return links


def parse_forum_html(
    html_text: str,
    problem_id: int,
    *,
    extracted_at: datetime | None = None,
) -> ProofLinksCache:
    """
    Parse forum HTML and return a ProofLinksCache.

    This is a pure function suitable for offline testing with fixtures.

    Args:
        html_text: Raw HTML content
        problem_id: Problem ID
        extracted_at: When extraction occurred (optional)

    Returns:
        ProofLinksCache with extracted links
    """
    if extracted_at is None:
        extracted_at = datetime.now(UTC)

    links = extract_proof_links_from_html(html_text, problem_id)

    return ProofLinksCache(
        problem_id=problem_id,
        forum_thread_url=f"https://www.erdosproblems.com/forum/thread/{problem_id}",
        extracted_at=extracted_at,
        links=links,
    )


def fetch_forum_thread(
    problem_id: int,
    *,
    timeout: float = 30.0,
    base_url: str = "https://www.erdosproblems.com",
) -> ForumFetchResult:
    """
    Fetch a forum thread from erdosproblems.com.

    Args:
        problem_id: The problem ID
        timeout: Request timeout in seconds
        base_url: Base URL (for testing)

    Returns:
        ForumFetchResult with HTML content and metadata

    Raises:
        ForumFetchError: If fetch fails
    """
    _rate_limit()

    url = f"{base_url}/forum/thread/{problem_id}"
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)

        if response.status_code == 404:
            raise ForumFetchError(
                f"Forum thread for problem {problem_id} not found (404)",
                status_code=404,
            )

        if response.status_code != 200:
            raise ForumFetchError(
                f"HTTP {response.status_code} fetching forum thread {problem_id}",
                status_code=response.status_code,
            )

        return ForumFetchResult(
            problem_id=problem_id,
            html_content=response.text,
            http_status=response.status_code,
            fetched_at=datetime.now(UTC),
        )

    except requests.Timeout as e:
        raise ForumFetchError(f"Timeout fetching forum thread {problem_id}") from e
    except requests.RequestException as e:
        raise ForumFetchError(f"Request error: {e}") from e


def fetch_and_parse_forum(
    problem_id: int,
    *,
    timeout: float = 30.0,
    base_url: str = "https://www.erdosproblems.com",
) -> ProofLinksCache:
    """
    Fetch and parse a forum thread.

    Args:
        problem_id: The problem ID
        timeout: Request timeout in seconds
        base_url: Base URL (for testing)

    Returns:
        ProofLinksCache with extracted links

    Raises:
        ForumFetchError: If fetch fails
    """
    result = fetch_forum_thread(problem_id, timeout=timeout, base_url=base_url)
    return parse_forum_html(
        result.html_content,
        problem_id,
        extracted_at=result.fetched_at,
    )


def save_proof_links_cache(
    cache: ProofLinksCache,
    *,
    cache_dir: Path | None = None,
) -> Path:
    """
    Save proof links cache to disk.

    Creates: <cache_dir>/<problem_id>/links.json

    Args:
        cache: ProofLinksCache to save
        cache_dir: Base directory for cache (default: data/sync_cache/proofs)

    Returns:
        Path to saved file
    """
    if cache_dir is None:
        cache_dir = Path("data/sync_cache/proofs")

    # Create problem-specific directory
    problem_dir = cache_dir / str(cache.problem_id)
    problem_dir.mkdir(parents=True, exist_ok=True)

    output_path = problem_dir / "links.json"

    # Serialize with Pydantic (handles datetime serialization)
    data = cache.model_dump(mode="json")

    # Atomic write via temp file
    tmp_path = output_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    tmp_path.replace(output_path)

    return output_path
