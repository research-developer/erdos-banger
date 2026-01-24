"""OpenAlex payload transformation helpers.

This module contains pure functions that transform OpenAlex API payloads into
our internal domain models. Keeping these separate from the HTTP client avoids
inflating `openalex.py` and makes the mapping logic easier to test in isolation.
"""

from __future__ import annotations

import re
from typing import Any

from erdos.core.models import OpenAccessStatus, ReferenceRecord


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Convert OpenAlex inverted index to plain text abstract.

    OpenAlex stores abstracts as inverted indexes where each word maps to
    its positions in the text. This function reconstructs the original text.

    Args:
        inverted_index: Word -> positions mapping from OpenAlex.

    Returns:
        Plain text abstract or None if input is empty/None.
    """
    if not inverted_index:
        return None

    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))

    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


_ARXIV_ABS_PREFIX = "https://arxiv.org/abs/"
_ARXIV_DOI_PREFIX = "https://doi.org/10.48550/arxiv."
_ARXIV_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


def _strip_arxiv_version(arxiv_id: str) -> str:
    """Normalize arXiv IDs by removing a trailing version suffix (e.g. v2)."""
    return _ARXIV_VERSION_SUFFIX_RE.sub("", arxiv_id)


def extract_arxiv_id(ids: dict[str, Any]) -> str | None:
    """Extract arXiv ID from an OpenAlex work `ids` object.

    Args:
        ids: OpenAlex IDs object containing various identifiers.

    Returns:
        arXiv ID (e.g., "2301.00001" or "math/0703001") or None if not present.
    """
    arxiv_url: object = ids.get("arxiv")
    if isinstance(arxiv_url, str) and arxiv_url:
        if arxiv_url.startswith(_ARXIV_ABS_PREFIX):
            return _strip_arxiv_version(arxiv_url[len(_ARXIV_ABS_PREFIX) :])
        if "/abs/" in arxiv_url:
            return _strip_arxiv_version(arxiv_url.split("/abs/")[-1])
        return _strip_arxiv_version(arxiv_url.rsplit("/", 1)[-1])

    doi_url: object = ids.get("doi")
    if (
        isinstance(doi_url, str)
        and doi_url
        and doi_url.lower().startswith(_ARXIV_DOI_PREFIX)
    ):
        return _strip_arxiv_version(doi_url[len(_ARXIV_DOI_PREFIX) :])

    return None


def _extract_arxiv_id_from_landing_page_url(url: str | None) -> str | None:
    """Extract arXiv ID from an OpenAlex landing_page_url.

    Supports:
    - arxiv.org/abs/<id>
    - arxiv.org/pdf/<id>(vN).pdf
    - doi.org/10.48550/arxiv.<id>
    """
    if not url or not isinstance(url, str):
        return None
    if url.lower().startswith(_ARXIV_DOI_PREFIX):
        candidate = url[len(_ARXIV_DOI_PREFIX) :]
        return _strip_arxiv_version(candidate)
    match = re.search(r"arxiv\.org/abs/([^\s?#]+)", url)
    if not match:
        match = re.search(r"arxiv\.org/pdf/([^\s?#]+)", url)
        if not match:
            return None
        candidate = match.group(1)
        if candidate.lower().endswith(".pdf"):
            candidate = candidate[: -len(".pdf")]
        return _strip_arxiv_version(candidate)
    candidate = match.group(1)
    return _strip_arxiv_version(candidate)


def extract_arxiv_id_from_work(work: dict[str, Any]) -> str | None:
    """Extract arXiv ID from a full OpenAlex work object.

    OpenAlex does not provide an `ids.arxiv` field. The arXiv identifier is usually
    discoverable via:
    - ids.doi (arXiv DataCite DOI: 10.48550/arxiv.<id>)
    - landing_page_url in primary_location or locations (arxiv.org/abs/<id> or
      doi.org/10.48550/arxiv.<id>)
    """
    ids = work.get("ids")
    if isinstance(ids, dict) and (arxiv_id := extract_arxiv_id(ids)):
        return arxiv_id

    primary_loc = work.get("primary_location")
    if isinstance(primary_loc, dict):
        landing = primary_loc.get("landing_page_url")
        if isinstance(landing, str) and (
            arxiv_id := _extract_arxiv_id_from_landing_page_url(landing)
        ):
            return arxiv_id

    for loc in work.get("locations", []):
        if not isinstance(loc, dict):
            continue
        landing = loc.get("landing_page_url")
        if isinstance(landing, str) and (
            arxiv_id := _extract_arxiv_id_from_landing_page_url(landing)
        ):
            return arxiv_id

    return None


def find_pdf_url(work: dict[str, Any]) -> str | None:
    """Find best PDF URL from OpenAlex work locations.

    Checks primary location first, then alternate locations.

    Args:
        work: OpenAlex work object.

    Returns:
        PDF URL or None if not available.
    """
    primary_loc = work.get("primary_location")
    primary: dict[str, Any] = primary_loc if isinstance(primary_loc, dict) else {}
    primary_pdf_url: object = primary.get("pdf_url")
    if isinstance(primary_pdf_url, str) and primary_pdf_url:
        return primary_pdf_url

    for loc in work.get("locations", []):
        if not isinstance(loc, dict):
            continue
        pdf_url = loc.get("pdf_url")
        if isinstance(pdf_url, str) and pdf_url:
            return pdf_url

    return None


def _map_oa_status(oa: dict[str, Any] | None) -> OpenAccessStatus:
    """Map OpenAlex OA status to our enum."""
    if not oa:
        return OpenAccessStatus.UNKNOWN

    status = oa.get("oa_status", "").lower()
    mapping = {
        "gold": OpenAccessStatus.GOLD,
        "green": OpenAccessStatus.GREEN,
        "bronze": OpenAccessStatus.BRONZE,
        "hybrid": OpenAccessStatus.HYBRID,
        "closed": OpenAccessStatus.CLOSED,
    }
    return mapping.get(status, OpenAccessStatus.UNKNOWN)


def _extract_doi(work: dict[str, Any]) -> str | None:
    """Extract DOI from an OpenAlex work object (normalized, no URL prefix)."""
    doi_raw = work.get("doi")
    if isinstance(doi_raw, str) and doi_raw:
        return doi_raw.removeprefix("https://doi.org/")

    ids = work.get("ids")
    if isinstance(ids, dict):
        doi_raw = ids.get("doi")
        if isinstance(doi_raw, str) and doi_raw:
            return doi_raw.removeprefix("https://doi.org/")
    return None


def _extract_authors(work: dict[str, Any]) -> list[str]:
    """Extract author display names from an OpenAlex work object."""
    authorships = work.get("authorships")
    if not isinstance(authorships, list):
        return []

    authors: list[str] = []
    for authorship in authorships:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        if not isinstance(author, dict):
            continue
        display_name = author.get("display_name")
        if isinstance(display_name, str) and display_name:
            authors.append(display_name)
    return authors


def _extract_venue(work: dict[str, Any]) -> str | None:
    """Extract venue display name from primary location."""
    primary_loc = work.get("primary_location")
    if not isinstance(primary_loc, dict):
        return None
    source = primary_loc.get("source")
    if not isinstance(source, dict):
        return None
    venue = source.get("display_name")
    return venue if isinstance(venue, str) and venue else None


def _extract_concepts(work: dict[str, Any], *, limit: int = 5) -> list[str]:
    """Extract up to `limit` concept display names from an OpenAlex work object."""
    raw_concepts = work.get("concepts")
    if not isinstance(raw_concepts, list):
        return []

    concepts: list[str] = []
    for concept in raw_concepts[:limit]:
        if not isinstance(concept, dict):
            continue
        name = concept.get("display_name")
        if isinstance(name, str) and name:
            concepts.append(name)
    return concepts


def openalex_to_reference(work: dict[str, Any]) -> ReferenceRecord:
    """Convert OpenAlex work to ReferenceRecord."""
    doi = _extract_doi(work)
    arxiv_id = extract_arxiv_id_from_work(work)
    authors = _extract_authors(work)
    venue = _extract_venue(work)
    concepts = _extract_concepts(work, limit=5)

    oa = work.get("open_access")
    oa_status = _map_oa_status(oa if isinstance(oa, dict) else None)

    return ReferenceRecord(
        doi=doi,
        arxiv_id=arxiv_id,
        title=work.get("title", ""),
        authors=authors,
        year=work.get("publication_year"),
        venue=venue,
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        openalex_id=work.get("id"),
        cited_by_count=work.get("cited_by_count"),
        concepts=concepts,
        pdf_url=find_pdf_url(work),
        oa_status=oa_status,
        source="openalex",
    )
