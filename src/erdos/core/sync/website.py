"""Website data extraction for erdosproblems.com (SPEC-035).

This module provides structured parsing of problem pages from erdosproblems.com.
It extracts:
- Problem statement (LaTeX math content)
- Status badge text (for cross-check only; submodule is authoritative)
- Tags
- References (citation keys)
- LaTeX source URL

All parsing uses stable HTML selectors based on semantic structure.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from erdos.core.constants import DEFAULT_HTTP_TIMEOUT
from erdos.core.rate_limiter import RateLimiter
from erdos.core.repo_root import repo_path
from erdos.core.sync.models import (
    WebsiteProblemData,
    WebsiteReferenceData,
    WebsiteSyncStatus,
)


logger = logging.getLogger(__name__)


# Rate limiting: Be polite to T. F. Bloom's server
WEBSITE_RATE_LIMIT = 2.0  # seconds between requests
_rate_limiter = RateLimiter(delay_seconds=WEBSITE_RATE_LIMIT)


class WebsiteParseError(Exception):
    """Raised when website parsing fails."""


class WebsiteFetchError(Exception):
    """Raised when website fetch fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class WebsiteFetchResult:
    """Result of fetching a problem page."""

    problem_id: int
    html_content: str
    http_status: int
    fetched_at: datetime


def fetch_problem_page(
    problem_id: int,
    *,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    base_url: str = "https://www.erdosproblems.com",
) -> WebsiteFetchResult:
    """
    Fetch a problem page from erdosproblems.com.

    Args:
        problem_id: The problem ID to fetch
        timeout: Request timeout in seconds
        base_url: Base URL (for testing)

    Returns:
        WebsiteFetchResult with HTML content and metadata

    Raises:
        WebsiteFetchError: If fetch fails
    """
    _rate_limiter.sleep_if_needed()

    url = f"{base_url}/{problem_id}"
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)

        if response.status_code == 404:
            raise WebsiteFetchError(
                f"Problem {problem_id} not found (404)",
                status_code=404,
            )

        if response.status_code != 200:
            raise WebsiteFetchError(
                f"HTTP {response.status_code} fetching problem {problem_id}",
                status_code=response.status_code,
            )

        return WebsiteFetchResult(
            problem_id=problem_id,
            html_content=response.text,
            http_status=response.status_code,
            fetched_at=datetime.now(UTC),
        )

    except requests.Timeout as e:
        raise WebsiteFetchError(f"Timeout fetching problem {problem_id}") from e
    except requests.RequestException as e:
        raise WebsiteFetchError(f"Request error: {e}") from e


def _extract_content(html_text: str) -> str | None:
    """Extract problem statement from <div id="content">."""
    match = re.search(r'<div\s+id="content"[^>]*>(.*?)</div>', html_text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Decode HTML entities like &#60; -> <
        content = html.unescape(content)
        return content if content else None
    return None


def _extract_title_from_html(html_text: str, problem_id: int) -> str:
    """Extract title from <title> tag or construct from problem ID."""
    match = re.search(
        r"<title>\s*(.*?)\s*</title>", html_text, re.DOTALL | re.IGNORECASE
    )
    if match:
        title = match.group(1).strip()
        # Clean up HTML entities
        title = html.unescape(title)
        return title
    return f"Erdős Problem #{problem_id}"


def _extract_status_badge(html_text: str) -> str | None:
    """
    Extract status badge text (e.g., 'PROVED', 'OPEN').

    Note: This is for cross-check only; submodule status is authoritative.
    """
    # Look for status in the tooltip span
    match = re.search(
        r'<span\s+class="tooltip">\s*(\w+)\s*<span\s+class="tooltiptext"',
        html_text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_tags(html_text: str) -> list[str]:
    """Extract tags from <div id="tags">."""
    tags_match = re.search(r'<div\s+id="tags"[^>]*>(.*?)</div>', html_text, re.DOTALL)
    if not tags_match:
        return []

    tags_html = tags_match.group(1)
    # Extract tag names from <a href="/tags/...">tag name</a>
    tag_links = re.findall(r'<a\s+href="/tags/[^"]*">([^<]+)</a>', tags_html)
    return [tag.strip() for tag in tag_links if tag.strip()]


def _extract_references(html_text: str) -> list[WebsiteReferenceData]:
    """
    Extract reference keys from the problem_id div.

    References appear as [Er55c], [ErGr80], etc.
    """
    # Look for the problem_id div
    pid_match = re.search(
        r'<div\s+id="problem_id"[^>]*>(.*?)</div>', html_text, re.DOTALL
    )
    if not pid_match:
        return []

    pid_html = pid_match.group(1)
    # Extract citation keys from [Key] patterns
    cite_keys = re.findall(r"\[([A-Za-z][A-Za-z0-9]*(?:,p\.\d+)?)\]", pid_html)

    refs: list[WebsiteReferenceData] = []
    seen: set[str] = set()
    for key in cite_keys:
        # Normalize: remove page references like ",p.619"
        normalized_key = re.sub(r",p\.\d+$", "", key)
        if normalized_key and normalized_key not in seen:
            seen.add(normalized_key)
            refs.append(WebsiteReferenceData(key=normalized_key))

    return refs


def _extract_latex_source_url(html_text: str, problem_id: int) -> str | None:
    """Extract LaTeX source URL if available."""
    match = re.search(
        r'<a\s+href="(/latex/\d+)"[^>]*>View the LaTeX source</a>', html_text
    )
    if match:
        return f"https://www.erdosproblems.com{match.group(1)}"
    # Try alternative pattern
    if f"/latex/{problem_id}" in html_text:
        return f"https://www.erdosproblems.com/latex/{problem_id}"
    return None


def parse_problem_html(
    html_text: str,
    problem_id: int,
    *,
    fetched_at: datetime | None = None,
) -> WebsiteProblemData:
    """
    Parse a problem page HTML into structured data.

    This is a pure function suitable for offline testing with fixtures.

    Args:
        html_text: Raw HTML content
        problem_id: Expected problem ID
        fetched_at: When the page was fetched (optional)

    Returns:
        WebsiteProblemData with extracted fields
    """
    title = _extract_title_from_html(html_text, problem_id)
    statement = _extract_content(html_text)
    status_badge = _extract_status_badge(html_text)
    tags = _extract_tags(html_text)
    references = _extract_references(html_text)
    latex_url = _extract_latex_source_url(html_text, problem_id)

    return WebsiteProblemData(
        problem_id=problem_id,
        title=title,
        statement=statement,
        tags=tags,
        references=references,
        status_badge_text=status_badge,
        latex_source_url=latex_url,
        fetched_at=fetched_at,
    )


def fetch_and_parse_problem(
    problem_id: int,
    *,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    base_url: str = "https://www.erdosproblems.com",
) -> tuple[WebsiteProblemData, WebsiteSyncStatus]:
    """
    Fetch and parse a problem page.

    Args:
        problem_id: The problem ID to fetch
        timeout: Request timeout in seconds
        base_url: Base URL (for testing)

    Returns:
        Tuple of (parsed data, sync status)

    Raises:
        WebsiteFetchError: If fetch fails
    """
    warnings: list[str] = []

    try:
        result = fetch_problem_page(problem_id, timeout=timeout, base_url=base_url)
    except WebsiteFetchError as e:
        status = WebsiteSyncStatus(
            problem_id=problem_id,
            fetched_at=datetime.now(UTC),
            http_status=e.status_code,
            parse_success=False,
            parse_error=str(e),
        )
        raise WebsiteFetchError(str(e), status_code=e.status_code) from e

    try:
        data = parse_problem_html(
            result.html_content,
            problem_id,
            fetched_at=result.fetched_at,
        )
    except Exception as e:  # normalize parser failures to WebsiteParseError
        status = WebsiteSyncStatus(
            problem_id=problem_id,
            fetched_at=result.fetched_at,
            http_status=result.http_status,
            parse_success=False,
            parse_error=str(e),
        )
        raise WebsiteParseError(f"Failed to parse problem {problem_id}: {e}") from e

    # Record warnings for missing fields
    if not data.statement:
        warnings.append("No statement found in HTML")
    if not data.tags:
        warnings.append("No tags found in HTML")

    status = WebsiteSyncStatus(
        problem_id=problem_id,
        fetched_at=result.fetched_at,
        http_status=result.http_status,
        parse_success=True,
        warnings=warnings,
    )

    return data, status


def fetch_latex_source(
    problem_id: int,
    *,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    base_url: str = "https://www.erdosproblems.com",
) -> str | None:
    """
    Fetch raw LaTeX source for a problem.

    Args:
        problem_id: The problem ID
        timeout: Request timeout in seconds
        base_url: Base URL (for testing)

    Returns:
        LaTeX source text, or None if not available
    """
    _rate_limiter.sleep_if_needed()

    url = f"{base_url}/latex/{problem_id}"
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True)

        if response.status_code != 200:
            logger.debug(
                "LaTeX source not available for problem %d: HTTP %d",
                problem_id,
                response.status_code,
            )
            return None

        return response.text

    except requests.RequestException as e:
        logger.debug("Failed to fetch LaTeX for problem %d: %s", problem_id, e)
        return None


def save_latex_source(
    problem_id: int,
    latex_content: str,
    *,
    output_dir: Path | None = None,
) -> Path:
    """
    Save LaTeX source to disk.

    Args:
        problem_id: The problem ID
        latex_content: LaTeX source text
        output_dir: Directory to save to (default: data/latex/)

    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = repo_path("data", "latex")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{problem_id}.tex"

    # Atomic write via temp file
    tmp_path = output_path.with_suffix(".tex.tmp")
    tmp_path.write_text(latex_content, encoding="utf-8")
    tmp_path.replace(output_path)

    return output_path
