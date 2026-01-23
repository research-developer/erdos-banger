# Spec 020: OpenAlex Integration

> Integrates OpenAlex as primary academic metadata source, replacing/augmenting arXiv + Crossref.

**Status:** Complete (core); CLI extensions deferred
**Target:** v1.2+
**Commit:** a09bf57, b2dcdfe
**Prerequisites (SSOT):**
- Ingest command: `docs/_archive/specs/spec-010-ingest-command.md`
- Literature paths: `src/erdos/core/literature_paths.py`

**Note (2026-01-23):** The OpenAlex client/provider integration was implemented, but the CLI extensions described in
Section 6 (`--enrich`, `--external`, `refs --enrich`) were **not** shipped. Current SSOT modules are:

- `src/erdos/core/clients/openalex.py`
- `src/erdos/core/providers/openalex.py`

---

## 0) Executive Summary

[OpenAlex](https://openalex.org/) is a fully open catalog of scholarly works with **271M+ works** (50k added daily). It aggregates data from:

- Crossref (DOI metadata)
- Microsoft Academic Graph (MAG)
- arXiv
- PubMed
- Institutional repositories

**Why OpenAlex over arXiv + Crossref separately:**

1. **Bigger dataset** - 271M works vs Crossref's ~140M
2. **Unified API** - One endpoint for DOIs, arXiv IDs, PMIDs
3. **No auth required** - 100k requests/day, 10 req/sec
4. **Richer metadata** - Concepts, topics, citations, authors, institutions
5. **Free forever** - 100% open data, open source

**Recommendation:** Use OpenAlex as PRIMARY source, with arXiv API as fallback for arXiv-specific data (LaTeX source, HTML).

---

## 1) API Overview

### Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `/works` | Search/filter works | `https://api.openalex.org/works?filter=doi:10.1234/example` |
| `/works/{id}` | Get single work | `https://api.openalex.org/works/W2741809807` |
| `/authors/{id}` | Get author info | `https://api.openalex.org/authors/A5023888391` |
| `/sources/{id}` | Get journal/venue info | `https://api.openalex.org/sources/S137773608` |

### Rate Limits

- **100,000 requests per day** per user
- **10 requests per second** max
- Add email for priority ("polite pool"): `?mailto=you@example.com`

### Authentication

**None required.** But adding email gets faster responses:

```python
# Recommended: add email to all requests
BASE_URL = "https://api.openalex.org"
params = {"mailto": "erdos-banger@example.com"}
```

---

## 2) Environment Configuration

```bash
# .env file - OpenAlex configuration

# Email for polite pool (faster responses)
ERDOS_MAILTO=your-email@example.com

# API key for authenticated access (optional but recommended)
# Get your key at: https://openalex.org/users/me
OPENALEX_API_KEY=your-api-key-here

# Optional: Use PyAlex library settings
# OPENALEX_EMAIL=your-email@example.com
```

**Authentication options:**
1. **API Key** (recommended) - Pass via `?api_key=<key>` query parameter
2. **Email only** - Uses "polite pool" for priority access

**Note:** OpenAlex is completely free. API key registration is optional but gives better rate limits.

---

## 3) Python Client Options

### Option A: PyAlex (Not used in `erdos-banger`)

`erdos-banger` intentionally uses direct HTTP (`requests` + `responses`) for deterministic tests and minimal dependencies. PyAlex is not a runtime dependency of this repository.

### Option B: Direct HTTP (SSOT; requests + responses for tests)

```python
import requests
import re
from typing import Any

class OpenAlexClient:
    """Minimal OpenAlex client using requests."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: str | None = None):
        self.email = email
        self.timeout = 30.0
        self.session = requests.Session()

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        params = dict(kwargs)
        if self.email:
            params["mailto"] = self.email
        return params

    def get_work_by_doi(self, doi: str) -> dict[str, Any]:
        """Fetch work by DOI."""
        url = f"{self.BASE_URL}/works/https://doi.org/{doi}"
        response = self.session.get(url, params=self._params(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_work_by_arxiv(self, arxiv_id: str) -> dict[str, Any]:
        """Fetch work by arXiv ID."""
        # OpenAlex does not support an ids.arxiv filter.
        # arXiv e-prints are deterministically addressable via their DataCite DOIs:
        #   10.48550/arxiv.<arxiv_id_without_version>
        arxiv_id_clean = re.sub(r"v\d+$", "", arxiv_id)
        doi = f"10.48550/arxiv.{arxiv_id_clean}"
        return self.get_work_by_doi(doi)

    def search_works(
        self,
        query: str,
        *,
        per_page: int = 25,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search works by title/abstract."""
        url = f"{self.BASE_URL}/works"
        params = self._params(search=query, per_page=per_page, page=page)
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("results", [])
```

---

## 4) Data Mapping

### OpenAlex Work → Our ReferenceRecord

```python
from typing import Any

from erdos.core.models import OpenAccessStatus, ReferenceRecord


def _map_oa_status(oa: dict[str, Any] | None) -> OpenAccessStatus:
    """Map OpenAlex OA status to our enum."""
    if not oa:
        return OpenAccessStatus.UNKNOWN

    status = (oa.get("oa_status") or "").lower()
    mapping = {
        "gold": OpenAccessStatus.GOLD,
        "green": OpenAccessStatus.GREEN,
        "bronze": OpenAccessStatus.BRONZE,
        "hybrid": OpenAccessStatus.HYBRID,
        "closed": OpenAccessStatus.CLOSED,
    }
    return mapping.get(status, OpenAccessStatus.UNKNOWN)


def openalex_to_reference(work: dict[str, Any]) -> ReferenceRecord:
    """Convert OpenAlex work to ReferenceRecord."""
    # Extract DOI (remove https://doi.org/ prefix). Prefer work.doi, fall back to ids.doi.
    doi_raw = work.get("doi") or ""
    if not doi_raw:
        ids = work.get("ids")
        if isinstance(ids, dict):
            doi_raw = ids.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

    arxiv_id = extract_arxiv_id_from_work(work)

    # Extract authors from authorships
    authors: list[str] = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author", {})
        if author.get("display_name"):
            authors.append(author["display_name"])

    # Extract venue from primary location
    primary_loc = work.get("primary_location", {}) or {}
    source = primary_loc.get("source", {}) or {}
    venue = source.get("display_name")

    # Extract concepts (top 5)
    concepts: list[str] = []
    for concept in work.get("concepts", [])[:5]:
        if concept.get("display_name"):
            concepts.append(concept["display_name"])

    # Map OA status
    oa_status = _map_oa_status(work.get("open_access", {}))

    return ReferenceRecord(
        # Identifiers
        doi=doi or None,
        arxiv_id=arxiv_id,

        # Metadata
        title=work.get("title", ""),
        authors=authors,
        year=work.get("publication_year"),
        venue=venue,

        # Abstract (OpenAlex stores as inverted index)
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),

        # OpenAlex-specific
        openalex_id=work.get("id"),
        cited_by_count=work.get("cited_by_count"),
        concepts=concepts,

        # URLs
        pdf_url=find_pdf_url(work),
        oa_status=oa_status,
        source="openalex",
    )


def extract_arxiv_id_from_work(work: dict) -> str | None:
    """Extract arXiv ID from an OpenAlex work object.

    OpenAlex does not guarantee a dedicated `ids.arxiv`. In practice, arXiv IDs are often
    discoverable via:
    - `ids.doi` when it is an arXiv DataCite DOI (10.48550/arxiv.<id>)
    - `primary_location.landing_page_url` when it points at `https://arxiv.org/abs/<id>`
    """
    ids = work.get("ids") or {}
    doi_url = ids.get("doi") or ""
    if isinstance(doi_url, str) and doi_url.lower().startswith("https://doi.org/10.48550/arxiv."):
        return doi_url.split("https://doi.org/10.48550/arxiv.", 1)[-1]

    landing = (work.get("primary_location") or {}).get("landing_page_url") or ""
    if isinstance(landing, str) and "arxiv.org/abs/" in landing:
        return landing.split("arxiv.org/abs/", 1)[-1].split("?", 1)[0].split("#", 1)[0]

    return None


def reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Convert OpenAlex inverted index to plain text abstract."""
    if not inverted_index:
        return None

    # Build word -> positions mapping
    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))

    # Sort by position and join
    words.sort(key=lambda x: x[0])
    return " ".join(word for _, word in words)


def find_pdf_url(work: dict) -> str | None:
    """Find best PDF URL from OpenAlex locations."""
    # Check primary location first
    primary = work.get("primary_location", {})
    if primary.get("pdf_url"):
        return primary["pdf_url"]

    # Check alternate locations
    for loc in work.get("locations", []):
        if loc.get("pdf_url"):
            return loc["pdf_url"]

    return None
```

---

## 5) Integration with Ingest Command

### Updated Ingest Flow

```text
erdos ingest PROBLEM_ID
    │
    ├─► Parse problem references (DOIs, arXiv IDs, URLs)
    │
    ├─► For each reference:
    │   │
    │   ├─► Try OpenAlex first (unified metadata)
    │   │   └─► Returns: title, authors, abstract, PDF URL, concepts
    │   │
    │   ├─► If arXiv ID present:
    │   │   └─► Fetch arXiv source tarball (for LaTeX)
    │   │   └─► (Optional) Fetch ar5iv HTML (for clean text)
    │   │
    │   └─► Write/merge manifest + extracts under literature/ (Spec 010)
    │
    └─► Indexing remains explicit (e.g., `erdos search --build-index` / Spec 006)
```

### Why Keep arXiv API?

OpenAlex provides metadata, but arXiv API provides:

1. **LaTeX source** - Higher quality than PDF extraction
2. **ar5iv HTML** - Clean structured text with math
3. **Version history** - Track paper revisions

**Strategy:** Use OpenAlex for metadata discovery, arXiv for content acquisition.

---

## 6) CLI Changes

### `erdos ingest` (Extended)

```text
erdos ingest PROBLEM_ID [OPTIONS]
```

**New Options**

- `--source openalex|arxiv|crossref`: Metadata source (default: openalex)
  - Implemented

### Deferred (Not Implemented)

The following CLI flags were proposed in this spec but are not implemented as of 2026-01-23:

- `erdos ingest --enrich`: Fetch additional metadata (citations, concepts)
- `erdos search --external`: Also search OpenAlex (not just local index)
- `erdos refs <id> --enrich`: Enrich references via OpenAlex citation graph

### `erdos search` (Extended)

```text
erdos search QUERY [OPTIONS]
```

**New Options**

*(Not implemented — see "Deferred" above.)*

### Examples

```bash
# Ingest with OpenAlex metadata
uv run erdos ingest 42
```

---

## 7) Implementation

### 7.1 New Module: `src/erdos/core/openalex_client.py`

```python
"""OpenAlex API client for academic metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from erdos.core.models import ReferenceRecord


@dataclass(frozen=True)
class OpenAlexConfig:
    """OpenAlex client configuration."""

    email: str | None = None
    timeout: float = 30.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> OpenAlexConfig:
        return cls(
            email=os.getenv("ERDOS_MAILTO") or os.getenv("OPENALEX_EMAIL"),
        )


class OpenAlexClient:
    """Client for OpenAlex API."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, config: OpenAlexConfig | None = None):
        self.config = config or OpenAlexConfig.from_env()
        self.session = requests.Session()

    def get_by_doi(self, doi: str) -> ReferenceRecord:
        """Fetch work by DOI."""
        ...

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord:
        """Fetch work by arXiv ID."""
        ...

    def search(self, query: str, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract."""
        ...

    def get_citations(self, work_id: str) -> list[ReferenceRecord]:
        """Get works that cite this work."""
        ...

    def get_references(self, work_id: str) -> list[ReferenceRecord]:
        """Get works cited by this work."""
        ...
```

### 7.2 Update: `src/erdos/core/ingest/fetch.py`

Add OpenAlex as primary metadata source:

```python
from erdos.core.openalex_client import OpenAlexClient
from erdos.core.arxiv_client import fetch_arxiv_atom, parse_arxiv_atom
from erdos.core.crossref_client import fetch_crossref_work, parse_crossref_work

# NOTE: In v1.1 the ingest pipeline fetches metadata in `fetch_reference_entry(...)`.
# Extend that pipeline to allow selecting the metadata source (default: openalex).
def _fetch_reference_metadata(
    ref_id: str,
    *,
    source: str = "openalex",
    mailto: str,
    timeout: float,
) -> ReferenceRecord:
    """Fetch reference metadata from a specified source."""

    if source == "openalex":
        client = OpenAlexClient()
        if is_doi(ref_id):
            return client.get_by_doi(ref_id)
        elif is_arxiv_id(ref_id):
            return client.get_by_arxiv(ref_id)
        else:
            raise ValueError(f"Unknown reference format: {ref_id}")

    elif source == "arxiv":
        return parse_arxiv_atom(fetch_arxiv_atom(ref_id))

    elif source == "crossref":
        if not is_doi(ref_id):
            raise ValueError(f"Crossref source requires DOI, got: {ref_id}")
        payload = fetch_crossref_work(ref_id, mailto=mailto, timeout=timeout)
        return parse_crossref_work(payload, doi=ref_id)

    # ... other sources
```

---

## 8) Dependencies

**SSOT (v1.1):** `requests` is already a core dependency (see `pyproject.toml`). This spec only needs an optional extra for PyAlex (if desired).

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
openalex = [
    "pyalex>=0.14.0",  # Optional: nicer API
]
```

**Note:** PyAlex is optional but recommended for interactive exploration; the SSOT implementation uses requests so tests can stay network-free with `responses`.

---

## 9) Acceptance Criteria

### Unit Tests

- `tests/unit/test_openalex_client.py`
  - Client initializes with email from env
  - DOI lookup returns valid ReferenceRecord
  - arXiv lookup returns valid ReferenceRecord
  - Abstract reconstruction works
  - Rate limiting is respected

### Integration Tests (requires network)

- `tests/integration/test_openalex_integration.py` (marked `requires_network`)
  - Real API calls return expected data
  - Error handling for missing works
  - Pagination works for large result sets

### Quality Gates

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## 10) Migration Path

### From Current (arXiv + Crossref) to OpenAlex

1. **v1.1**: Ship with arXiv + Crossref (current spec-010)
2. **v1.2**: Add OpenAlex client alongside existing clients
3. **v1.3**: Make OpenAlex default, deprecate direct Crossref calls
4. **v2.0**: Remove Crossref client (OpenAlex includes Crossref data)

**No breaking changes** - OpenAlex augments existing functionality.

---

## References

- OpenAlex Documentation: `https://docs.openalex.org/`
- OpenAlex API Guide for LLMs: `https://docs.openalex.org/api-guide-for-llms`
- PyAlex Library: `https://github.com/J535D165/pyalex`
- OpenAlex Tutorials: `https://github.com/ourresearch/openalex-api-tutorials`
- OpenAlex vs Crossref Analysis: `https://arxiv.org/html/2512.16434v1`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-19 | Initial spec |
