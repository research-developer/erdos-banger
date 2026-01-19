# Spec 020: OpenAlex Integration

> Integrates OpenAlex as primary academic metadata source, replacing/augmenting arXiv + Crossref.

**Status:** Ready
**Target:** v1.2+
**Prerequisites (SSOT):**
- Ingest command: `docs/specs/spec-010-ingest-command.md`
- Literature paths: `src/erdos/core/literature_paths.py`

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

# Optional: Email for polite pool (faster responses)
# No API key needed!
ERDOS_MAILTO=your-email@example.com

# Optional: Use PyAlex library settings
OPENALEX_EMAIL=your-email@example.com
```

**Note:** OpenAlex is completely free. No API key. No registration. Just be polite (add email).

---

## 3) Python Client Options

### Option A: PyAlex (Recommended)

[PyAlex](https://github.com/J535D165/pyalex) is a lightweight Python wrapper for OpenAlex.

```bash
uv add pyalex
```

```python
from pyalex import Works, Authors, config

# Configure email for polite pool
config.email = "erdos-banger@example.com"

# Retry configuration
config.max_retries = 3
config.retry_backoff_factor = 0.5
config.retry_http_codes = [429, 500, 503]

# Search by DOI
work = Works()["https://doi.org/10.1038/nature12373"]
print(work["title"])
print(work["abstract_inverted_index"])  # PyAlex converts to text

# Search by arXiv ID
arxiv_works = Works().filter(ids={"openalex": "https://arxiv.org/abs/2301.00001"}).get()

# Search by title (fuzzy)
works = Works().search("Erdős conjecture sum-free sets").get()

# Filter by multiple criteria
recent_math = (
    Works()
    .filter(concepts={"id": "C33923547"})  # Mathematics concept
    .filter(publication_year=">2020")
    .sort(cited_by_count="desc")
    .get()
)
```

### Option B: Direct HTTP (No Dependency)

```python
import httpx
from typing import Any

class OpenAlexClient:
    """Minimal OpenAlex client using httpx."""

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: str | None = None):
        self.email = email
        self.client = httpx.Client(timeout=30.0)

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        params = dict(kwargs)
        if self.email:
            params["mailto"] = self.email
        return params

    def get_work_by_doi(self, doi: str) -> dict[str, Any]:
        """Fetch work by DOI."""
        url = f"{self.BASE_URL}/works/https://doi.org/{doi}"
        response = self.client.get(url, params=self._params())
        response.raise_for_status()
        return response.json()

    def get_work_by_arxiv(self, arxiv_id: str) -> dict[str, Any]:
        """Fetch work by arXiv ID."""
        # OpenAlex indexes arXiv via DOI
        url = f"{self.BASE_URL}/works"
        params = self._params(filter=f"ids.arxiv:{arxiv_id}")
        response = self.client.get(url, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            raise ValueError(f"No work found for arXiv:{arxiv_id}")
        return results[0]

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
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
```

---

## 4) Data Mapping

### OpenAlex Work → Our ReferenceRecord

```python
from erdos.core.models import ReferenceRecord

def openalex_to_reference(work: dict) -> ReferenceRecord:
    """Convert OpenAlex work to our ReferenceRecord model."""
    return ReferenceRecord(
        # Identifiers
        doi=work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
        arxiv_id=extract_arxiv_id(work.get("ids", {})),

        # Metadata
        title=work.get("title", ""),
        authors=[a["author"]["display_name"] for a in work.get("authorships", [])],
        year=work.get("publication_year"),
        journal=work.get("primary_location", {}).get("source", {}).get("display_name"),

        # Abstract (OpenAlex stores as inverted index)
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),

        # OpenAlex-specific
        openalex_id=work.get("id"),
        cited_by_count=work.get("cited_by_count", 0),
        concepts=[c["display_name"] for c in work.get("concepts", [])[:5]],

        # URLs
        pdf_url=find_pdf_url(work),
        open_access=work.get("open_access", {}).get("is_oa", False),
    )


def extract_arxiv_id(ids: dict) -> str | None:
    """Extract arXiv ID from OpenAlex IDs."""
    arxiv_url = ids.get("arxiv")
    if arxiv_url:
        # Format: https://arxiv.org/abs/2301.00001
        return arxiv_url.split("/")[-1]
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

```
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
    │   │   └─► Fetch ar5iv HTML (for clean text)
    │   │
    │   └─► Store in literature/manifests/
    │
    └─► Update search index
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
- `--enrich`: Fetch additional metadata (citations, concepts)

### `erdos search` (Extended)

```text
erdos search QUERY [OPTIONS]
```

**New Options**

- `--external`: Also search OpenAlex (not just local index)
- `--limit N`: Max results from external search

### Examples

```bash
# Ingest with OpenAlex metadata
uv run erdos ingest 42

# Search OpenAlex directly
uv run erdos search "sum-free sets" --external --limit 10

# Get rich metadata for a DOI
uv run erdos refs 42 --enrich
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

import httpx

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
        self.client = httpx.Client(timeout=self.config.timeout)

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

### 7.2 Update: `src/erdos/core/ingest.py`

Add OpenAlex as primary metadata source:

```python
from erdos.core.openalex_client import OpenAlexClient
from erdos.core.arxiv_client import ArxivClient

def ingest_reference(ref_id: str, source: str = "openalex") -> ReferenceRecord:
    """Ingest reference metadata from specified source."""

    if source == "openalex":
        client = OpenAlexClient()
        if is_doi(ref_id):
            return client.get_by_doi(ref_id)
        elif is_arxiv_id(ref_id):
            return client.get_by_arxiv(ref_id)
        else:
            raise ValueError(f"Unknown reference format: {ref_id}")

    elif source == "arxiv":
        client = ArxivClient()
        return client.get_metadata(ref_id)

    # ... other sources
```

---

## 8) Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing deps
    "httpx>=0.27.0",  # Already likely present
]

[project.optional-dependencies]
openalex = [
    "pyalex>=0.14.0",  # Optional: nicer API
]
```

**Note:** httpx is likely already a dependency. PyAlex is optional but recommended.

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
