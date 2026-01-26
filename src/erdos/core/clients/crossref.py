"""Crossref API client for literature metadata.

This module provides functions to fetch and parse metadata from the Crossref
REST API.

API Reference: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
"""

import logging
import time
from typing import cast
from urllib.parse import quote

from erdos.core.clients.json_response import response_json_or_raise
from erdos.core.models import ReferenceRecord
from erdos.core.retry import fetch_with_retry


logger = logging.getLogger(__name__)

_CrossrefMessage = dict[str, object]


def _require_crossref_message(payload: dict[str, object]) -> _CrossrefMessage:
    """Extract and validate the Crossref `message` object."""
    status = payload.get("status")
    if status == "error":
        message = payload.get("message", "Unknown error")
        raise ValueError(f"Crossref error: {message}")

    message = payload.get("message")
    if not message or not isinstance(message, dict):
        raise ValueError("Invalid Crossref response: missing 'message' object")
    return message


def _extract_title(message: _CrossrefMessage) -> object:
    """Extract the required title field from Crossref message."""
    title_list = message.get("title")
    if not title_list or not isinstance(title_list, list) or not title_list[0]:
        raise ValueError("Missing required field: title")
    return title_list[0]


def _extract_authors(message: _CrossrefMessage) -> list[str]:
    """Extract author display names from Crossref message."""
    authors: list[str] = []
    author_list = message.get("author", [])
    if not isinstance(author_list, list):
        return authors

    for author in author_list:
        if not isinstance(author, dict):
            continue
        given = author.get("given", "")
        family = author.get("family", "")
        if family:
            authors.append(f"{given} {family}".strip())
    return authors


def _extract_year(message: _CrossrefMessage) -> object | None:
    """Extract publication year from Crossref message (best-effort)."""
    published_print = message.get("published-print")
    if not published_print or not isinstance(published_print, dict):
        return None

    date_parts = published_print.get("date-parts")
    if not date_parts or not isinstance(date_parts, list):
        return None

    first = date_parts[0] if date_parts else None
    if not first or not isinstance(first, list):
        return None

    return first[0] if first else None


def _extract_venue(message: _CrossrefMessage) -> object | None:
    """Extract the container title (journal/venue) from Crossref message."""
    container_title = message.get("container-title")
    if not container_title or not isinstance(container_title, list):
        return None
    return container_title[0] if container_title else None


def parse_crossref_work(payload: dict[str, object], *, doi: str) -> ReferenceRecord:
    """Parse Crossref work JSON into a ReferenceRecord.

    Args:
        payload: Crossref API JSON response (full response object).
        doi: The DOI for this work (used as identifier).

    Returns:
        ReferenceRecord with Crossref metadata.

    Raises:
        ValueError: If response is an error or missing required fields.
    """
    message = _require_crossref_message(payload)
    title = _extract_title(message)
    authors = _extract_authors(message)
    year = _extract_year(message)
    venue = _extract_venue(message)

    return ReferenceRecord(
        doi=doi,
        title=str(title),
        authors=authors,
        year=int(year) if isinstance(year, int) else None,
        venue=str(venue) if isinstance(venue, str) and venue else None,
        source="crossref",
    )


def fetch_crossref_work(
    doi: str, *, mailto: str, timeout: float = 30.0
) -> dict[str, object]:
    """Fetch Crossref work metadata via REST API.

    Args:
        doi: The DOI to retrieve (e.g., "10.1007/BF01940595").
        mailto: Contact email for Crossref polite pool.
        timeout: HTTP timeout in seconds.

    Returns:
        Crossref API JSON response as a dictionary.

    Raises:
        requests.HTTPError: If HTTP request fails (e.g., 404 for not found).
        requests.Timeout: If request times out after all retries.
        requests.ConnectionError: If connection fails after all retries.
    """
    encoded_doi = quote(doi, safe="/")
    url = f"https://api.crossref.org/works/{encoded_doi}"
    params = {"mailto": mailto}
    headers = {
        "User-Agent": f"erdos-banger/1.0 (https://github.com/The-Obstacle-Is-The-Way/erdos-banger; mailto:{mailto})"
    }

    logger.debug("Fetching Crossref metadata for DOI: %s", doi)
    start_time = time.monotonic()

    response = fetch_with_retry(url, timeout=timeout, params=params, headers=headers)
    elapsed = time.monotonic() - start_time
    logger.debug(
        "Crossref response: %d bytes in %.2fs (status %d)",
        len(response.content),
        elapsed,
        response.status_code,
    )

    data = response_json_or_raise(
        response,
        url=url,
        service="Crossref",
        logger=logger,
    )
    if not isinstance(data, dict):
        raise ValueError(f"Crossref invalid JSON response type: {type(data).__name__}")
    return cast("dict[str, object]", data)
