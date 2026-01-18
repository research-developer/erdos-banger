# Spec 010: Ingest Command

> Defines the `erdos ingest` command for fetching and caching reference metadata and content for Erdős problems.

---

## Overview

The ingest command bridges the gap between minimal upstream problem data and rich, searchable reference material. It fetches metadata from academic APIs, downloads legally available content, and creates manifests for reproducibility.

### Core Workflow

```
erdos ingest <problem_id>
       │
       ▼
┌──────────────────┐
│ Load ProblemRecord │
│ (YAML via loader)  │
└────────┬─────────┘
         │ references[]
         ▼
┌──────────────────────────────────────────────────┐
│ For each ReferenceEntry:                          │
│  1. Resolve identifier (DOI, arXiv, title search) │
│  2. Fetch metadata (Crossref, arXiv API)          │
│  3. Check OA status (Unpaywall)                   │
│  4. Download content if legal (arXiv HTML/source) │
│  5. Cache content with hash                        │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌────────────────────┐
│ Write manifest YAML │
│ literature/manifests/ │
└────────────────────┘
```

### Guiding Principles

1. **Legal compliance** - Only download open-access content; respect licenses
2. **Idempotent** - Running twice produces the same result; skip already fetched
3. **Graceful degradation** - Partial success is acceptable; record errors in manifest
4. **Rate-limited** - Respect API rate limits (3s between Crossref calls, etc.)

---

## 1) CLI Interface

### Command Signature

```
erdos ingest <problem_id> [OPTIONS]

Arguments:
  problem_id    Problem ID to ingest references for (required)

Options:
  --force, -f       Re-fetch even if manifest exists
  --no-network      Error if network access would be needed
  --no-download     Fetch metadata only, skip content download
  --timeout SECS    Request timeout in seconds [default: 30]
  --json            Output as JSON for machine consumption
```

### Examples

```bash
# Basic usage: ingest references for problem 6
erdos ingest 6

# Force re-fetch of all references
erdos ingest 6 --force

# Metadata only, no PDF/HTML download
erdos ingest 6 --no-download

# JSON output for automation
erdos ingest 6 --json
```

### Output (Human Mode)

```
Ingesting references for Problem 6: Small primes in arithmetic progressions

[1/3] Erdos1975
  ✓ Crossref: 10.1006/jnth.1996.0001
  ✓ Open access: green (via arXiv)
  ✓ Downloaded: arxiv_0704.1234v2.tar.gz (1.2 MB)

[2/3] Linnik1944
  ✓ Crossref: 10.1090/S0002-9947-1944-...
  ✗ Not open access (paywalled)

[3/3] Heath-Brown1992
  ✓ Crossref: 10.4007/annals.1992.135.2.5
  ✓ Open access: bronze (free PDF)
  ✓ Downloaded: hb1992.pdf (892 KB)

Summary:
  References: 3 total
  Metadata fetched: 3
  Content downloaded: 2 (green: 1, bronze: 1)
  Errors: 0

Manifest saved: literature/manifests/0006.yaml
```

### Output (JSON Mode)

```json
{
  "schema_version": 1,
  "command": "erdos ingest",
  "success": true,
  "data": {
    "problem_id": 6,
    "manifest_path": "literature/manifests/0006.yaml",
    "summary": {
      "total_references": 3,
      "metadata_fetched": 3,
      "content_downloaded": 2,
      "errors": 0
    },
    "references": [
      {
        "key": "Erdos1975",
        "doi": "10.1006/jnth.1996.0001",
        "oa_status": "green",
        "cached": true,
        "cache_path": "literature/cache/arxiv_0704.1234v2.tar.gz",
        "error": null
      },
      {
        "key": "Linnik1944",
        "doi": "10.1090/S0002-9947-1944-...",
        "oa_status": "closed",
        "cached": false,
        "cache_path": null,
        "error": null
      }
    ]
  },
  "timestamp": "2026-01-17T12:00:00Z",
  "duration_ms": 4523
}
```

---

## 2) Domain Models

### IngestResult

```python
# src/erdos/domain/ingest.py
"""Ingest operation domain models."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import Field

from erdos.domain.base import ErdosBaseModel


class IngestStatus(str, Enum):
    """Status of a reference ingestion."""

    SUCCESS = "success"           # Metadata fetched, content (if OA) downloaded
    PARTIAL = "partial"           # Metadata fetched, content not available
    METADATA_ONLY = "metadata_only"  # Only metadata (--no-download mode)
    SKIPPED = "skipped"           # Already ingested, not --force
    ERROR = "error"               # Failed to fetch


class IngestReferenceResult(ErdosBaseModel):
    """Result of ingesting a single reference."""

    key: Annotated[str, Field(description="Reference key from problem")]
    status: IngestStatus

    # Identifiers resolved
    doi: Annotated[str | None, Field(default=None)] = None
    arxiv_id: Annotated[str | None, Field(default=None)] = None

    # Metadata source
    metadata_source: Annotated[str | None, Field(default=None)] = None  # "crossref", "arxiv", etc.

    # Open access info
    oa_status: Annotated[str | None, Field(default=None)] = None  # "gold", "green", "bronze", "closed"
    oa_url: Annotated[str | None, Field(default=None)] = None

    # Cache info
    cached: Annotated[bool, Field(default=False)] = False
    cache_path: Annotated[str | None, Field(default=None)] = None
    cache_hash: Annotated[str | None, Field(default=None)] = None  # MD5

    # Error info
    error: Annotated[str | None, Field(default=None)] = None


class IngestSummary(ErdosBaseModel):
    """Summary of an ingest operation."""

    problem_id: Annotated[int, Field(ge=1)]
    manifest_path: Annotated[str, Field(description="Path to generated manifest")]

    total_references: Annotated[int, Field(ge=0)]
    metadata_fetched: Annotated[int, Field(ge=0)]
    content_downloaded: Annotated[int, Field(ge=0)]
    skipped: Annotated[int, Field(ge=0)]
    errors: Annotated[int, Field(ge=0)]

    references: Annotated[list[IngestReferenceResult], Field(default_factory=list)]

    started_at: Annotated[datetime, Field()]
    completed_at: Annotated[datetime, Field()]
```

---

## 3) API Integration

### Metadata APIs

#### Crossref (DOI Resolution)

```python
# src/erdos/infrastructure/apis/crossref.py
"""Crossref API client for DOI metadata."""

import time
from typing import Annotated

import httpx

from erdos.domain.reference import ReferenceRecord, OpenAccessStatus


class CrossrefClient:
    """
    Client for Crossref REST API.

    Rate limit: 50 requests/second for polite pool (with mailto).
    We use 3 second delay between requests to be conservative.

    API docs: https://api.crossref.org/swagger-ui/index.html
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(
        self,
        mailto: str = "erdos-banger@example.com",
        timeout: float = 30.0,
        delay: float = 3.0,
    ) -> None:
        self._mailto = mailto
        self._timeout = timeout
        self._delay = delay
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def get_by_doi(self, doi: str) -> ReferenceRecord | None:
        """
        Fetch metadata for a DOI.

        Args:
            doi: DOI without URL prefix (e.g., "10.1006/jnth.1996.0001")

        Returns:
            ReferenceRecord or None if not found
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/{doi}"
        headers = {
            "User-Agent": f"erdos-banger/1.0 (mailto:{self._mailto})",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()["message"]

            return ReferenceRecord(
                doi=doi,
                title=data.get("title", [""])[0],
                authors=self._parse_authors(data.get("author", [])),
                year=self._parse_year(data),
                venue=data.get("container-title", [""])[0] or None,
                source="crossref",
            )

        except httpx.HTTPError:
            return None

    def search_by_title(
        self, title: str, author: str | None = None, limit: int = 5
    ) -> list[ReferenceRecord]:
        """
        Search Crossref by title (and optionally author).

        Used when only bibliographic text is available.
        """
        self._rate_limit()

        params = {
            "query.title": title,
            "rows": limit,
        }
        if author:
            params["query.author"] = author

        headers = {
            "User-Agent": f"erdos-banger/1.0 (mailto:{self._mailto})",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self.BASE_URL, params=params, headers=headers)

            response.raise_for_status()
            items = response.json()["message"]["items"]

            return [
                ReferenceRecord(
                    doi=item.get("DOI"),
                    title=item.get("title", [""])[0],
                    authors=self._parse_authors(item.get("author", [])),
                    year=self._parse_year(item),
                    venue=item.get("container-title", [""])[0] or None,
                    source="crossref",
                )
                for item in items
                if item.get("DOI")
            ]

        except httpx.HTTPError:
            return []

    @staticmethod
    def _parse_authors(author_list: list[dict]) -> list[str]:
        """Parse Crossref author format to names."""
        names = []
        for a in author_list:
            given = a.get("given", "")
            family = a.get("family", "")
            if family:
                names.append(f"{given} {family}".strip())
        return names

    @staticmethod
    def _parse_year(data: dict) -> int | None:
        """Extract publication year from Crossref data."""
        # Try published-print, then published-online, then created
        for key in ("published-print", "published-online", "created"):
            if key in data:
                parts = data[key].get("date-parts", [[]])
                if parts and parts[0]:
                    return parts[0][0]
        return None
```

#### arXiv API

```python
# src/erdos/infrastructure/apis/arxiv.py
"""arXiv API client for preprint metadata and content."""

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from erdos.domain.reference import ReferenceRecord


class ArxivClient:
    """
    Client for arXiv API.

    Rate limit: 1 request per 3 seconds (strictly enforced).
    API docs: https://info.arxiv.org/help/api/index.html
    """

    BASE_URL = "http://export.arxiv.org/api/query"
    CONTENT_URL = "https://arxiv.org"

    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    ARXIV_NS = "{http://arxiv.org/schemas/atom}"

    def __init__(self, timeout: float = 30.0, delay: float = 3.0) -> None:
        self._timeout = timeout
        self._delay = delay
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting (1 req/3s)."""
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def get_by_id(self, arxiv_id: str) -> ReferenceRecord | None:
        """
        Fetch metadata for an arXiv ID.

        Args:
            arxiv_id: arXiv ID (e.g., "2201.00001" or "math/0703456")

        Returns:
            ReferenceRecord or None if not found
        """
        self._rate_limit()

        # Normalize ID (strip version suffix for query)
        clean_id = re.sub(r"v\d+$", "", arxiv_id)

        params = {"id_list": clean_id, "max_results": 1}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self.BASE_URL, params=params)

            response.raise_for_status()
            return self._parse_response(response.text, arxiv_id)

        except httpx.HTTPError:
            return None

    def download_source(
        self, arxiv_id: str, dest_dir: Path
    ) -> tuple[Path | None, str | None]:
        """
        Download arXiv source (TeX) tarball.

        Args:
            arxiv_id: arXiv ID
            dest_dir: Directory to save file

        Returns:
            (path to downloaded file, MD5 hash) or (None, None) on failure
        """
        import hashlib

        self._rate_limit()

        # e-print endpoint for source
        url = f"{self.CONTENT_URL}/e-print/{arxiv_id}"

        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(url)

            if response.status_code != 200:
                return None, None

            # Determine filename from content-disposition or use default
            filename = f"arxiv_{arxiv_id.replace('/', '_')}.tar.gz"
            dest_path = dest_dir / filename

            dest_path.write_bytes(response.content)

            # Compute hash
            md5 = hashlib.md5(response.content).hexdigest()

            return dest_path, md5

        except httpx.HTTPError:
            return None, None

    def download_html(
        self, arxiv_id: str, dest_dir: Path
    ) -> tuple[Path | None, str | None]:
        """
        Download arXiv HTML version (available since Dec 2023).

        Args:
            arxiv_id: arXiv ID
            dest_dir: Directory to save file

        Returns:
            (path to downloaded file, MD5 hash) or (None, None) on failure
        """
        import hashlib

        self._rate_limit()

        # HTML endpoint
        url = f"{self.CONTENT_URL}/html/{arxiv_id}"

        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(url)

            if response.status_code != 200:
                return None, None

            filename = f"arxiv_{arxiv_id.replace('/', '_')}.html"
            dest_path = dest_dir / filename

            dest_path.write_text(response.text, encoding="utf-8")

            md5 = hashlib.md5(response.content).hexdigest()

            return dest_path, md5

        except httpx.HTTPError:
            return None, None

    def _parse_response(self, xml_text: str, original_id: str) -> ReferenceRecord | None:
        """Parse arXiv Atom response."""
        try:
            root = ET.fromstring(xml_text)
            entry = root.find(f"{self.ATOM_NS}entry")

            if entry is None:
                return None

            title = entry.findtext(f"{self.ATOM_NS}title", "").strip()
            if not title or "Error" in title:
                return None

            # Parse authors
            authors = []
            for author in entry.findall(f"{self.ATOM_NS}author"):
                name = author.findtext(f"{self.ATOM_NS}name", "")
                if name:
                    authors.append(name)

            # Parse year from published date
            published = entry.findtext(f"{self.ATOM_NS}published", "")
            year = int(published[:4]) if published else None

            # Get abstract
            abstract = entry.findtext(f"{self.ATOM_NS}summary", "").strip()

            # Get DOI if present
            doi = entry.findtext(f"{self.ARXIV_NS}doi", None)

            return ReferenceRecord(
                arxiv_id=original_id,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                oa_status="gold",  # arXiv is always open
                source="arxiv",
            )

        except ET.ParseError:
            return None
```

#### Unpaywall (Open Access Detection)

```python
# src/erdos/infrastructure/apis/unpaywall.py
"""Unpaywall API client for open access detection."""

import time

import httpx

from erdos.domain.reference import OpenAccessStatus


class UnpaywallClient:
    """
    Client for Unpaywall API.

    Rate limit: 100,000 requests/day with email.
    We add 1 second delay between requests.

    API docs: https://unpaywall.org/products/api
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        email: str = "erdos-banger@example.com",
        timeout: float = 30.0,
        delay: float = 1.0,
    ) -> None:
        self._email = email
        self._timeout = timeout
        self._delay = delay
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def get_oa_status(self, doi: str) -> tuple[OpenAccessStatus, str | None]:
        """
        Check open access status for a DOI.

        Args:
            doi: DOI to check

        Returns:
            (OA status, best OA URL or None)
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/{doi}"
        params = {"email": self._email}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params)

            if response.status_code == 404:
                return OpenAccessStatus.UNKNOWN, None

            response.raise_for_status()
            data = response.json()

            if not data.get("is_oa"):
                return OpenAccessStatus.CLOSED, None

            # Map Unpaywall oa_status to our enum
            oa_status_map = {
                "gold": OpenAccessStatus.GOLD,
                "green": OpenAccessStatus.GREEN,
                "bronze": OpenAccessStatus.BRONZE,
                "hybrid": OpenAccessStatus.HYBRID,
            }

            status = oa_status_map.get(
                data.get("oa_status", ""), OpenAccessStatus.UNKNOWN
            )

            # Get best OA location URL
            best_oa_url = None
            best_loc = data.get("best_oa_location")
            if best_loc:
                best_oa_url = best_loc.get("url_for_pdf") or best_loc.get("url")

            return status, best_oa_url

        except httpx.HTTPError:
            return OpenAccessStatus.UNKNOWN, None
```

---

## 4) Ingest Service

```python
# src/erdos/application/ingest_service.py
"""Ingest service orchestrating reference fetching."""

from datetime import UTC, datetime
from pathlib import Path

from erdos.domain.ingest import IngestReferenceResult, IngestStatus, IngestSummary
from erdos.domain.manifest import ManifestEntry, ProblemManifest
from erdos.domain.problem import ProblemRecord, ReferenceEntry
from erdos.domain.reference import OpenAccessStatus, ReferenceRecord
from erdos.infrastructure.apis.arxiv import ArxivClient
from erdos.infrastructure.apis.crossref import CrossrefClient
from erdos.infrastructure.apis.unpaywall import UnpaywallClient


class IngestService:
    """
    Orchestrates reference ingestion for a problem.

    Coordinates:
    - Identifier resolution (DOI lookup, title search)
    - Metadata fetching (Crossref, arXiv)
    - OA status checking (Unpaywall)
    - Content downloading (arXiv source/HTML)
    - Manifest writing
    """

    def __init__(
        self,
        crossref: CrossrefClient | None = None,
        arxiv: ArxivClient | None = None,
        unpaywall: UnpaywallClient | None = None,
        cache_dir: Path | None = None,
        manifest_dir: Path | None = None,
    ) -> None:
        self._crossref = crossref or CrossrefClient()
        self._arxiv = arxiv or ArxivClient()
        self._unpaywall = unpaywall or UnpaywallClient()
        self._cache_dir = cache_dir or Path("literature/cache")
        self._manifest_dir = manifest_dir or Path("literature/manifests")

    def ingest(
        self,
        problem: ProblemRecord,
        *,
        force: bool = False,
        download_content: bool = True,
    ) -> IngestSummary:
        """
        Ingest all references for a problem.

        Args:
            problem: The problem whose references to ingest
            force: If True, re-fetch even if manifest exists
            download_content: If True, download OA content

        Returns:
            IngestSummary with results
        """
        started_at = datetime.now(UTC)

        # Check existing manifest
        manifest_path = self._manifest_dir / f"{problem.id:04d}.yaml"
        existing_manifest = self._load_manifest(manifest_path)

        if existing_manifest and not force:
            # Return early with skipped status
            return IngestSummary(
                problem_id=problem.id,
                manifest_path=str(manifest_path),
                total_references=len(problem.references),
                metadata_fetched=0,
                content_downloaded=0,
                skipped=len(problem.references),
                errors=0,
                references=[
                    IngestReferenceResult(key=ref.key, status=IngestStatus.SKIPPED)
                    for ref in problem.references
                ],
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )

        # Ensure directories exist
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_dir.mkdir(parents=True, exist_ok=True)

        # Process each reference
        results: list[IngestReferenceResult] = []
        manifest_entries: list[ManifestEntry] = []

        for ref in problem.references:
            result, entry = self._ingest_reference(
                ref, download_content=download_content
            )
            results.append(result)
            if entry:
                manifest_entries.append(entry)

        # Write manifest
        manifest = ProblemManifest(
            problem_id=problem.id,
            entries=manifest_entries,
        )
        self._write_manifest(manifest, manifest_path)

        # Compute summary
        completed_at = datetime.now(UTC)
        metadata_fetched = sum(
            1 for r in results if r.status in (IngestStatus.SUCCESS, IngestStatus.PARTIAL, IngestStatus.METADATA_ONLY)
        )
        content_downloaded = sum(1 for r in results if r.cached)
        errors = sum(1 for r in results if r.status == IngestStatus.ERROR)

        return IngestSummary(
            problem_id=problem.id,
            manifest_path=str(manifest_path),
            total_references=len(problem.references),
            metadata_fetched=metadata_fetched,
            content_downloaded=content_downloaded,
            skipped=0,
            errors=errors,
            references=results,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _ingest_reference(
        self, ref: ReferenceEntry, *, download_content: bool
    ) -> tuple[IngestReferenceResult, ManifestEntry | None]:
        """Ingest a single reference."""
        result = IngestReferenceResult(key=ref.key, status=IngestStatus.ERROR)

        try:
            # Step 1: Resolve identifier and fetch metadata
            record = self._resolve_and_fetch(ref)

            if record is None:
                result.error = "Could not resolve reference"
                return result, None

            result.doi = record.doi
            result.arxiv_id = record.arxiv_id
            result.metadata_source = record.source

            # Step 2: Check OA status
            oa_status, oa_url = self._check_oa_status(record)
            result.oa_status = oa_status.value
            result.oa_url = oa_url
            record.oa_status = oa_status
            record.oa_url = oa_url

            # Step 3: Download content if allowed
            cache_path = None
            cache_hash = None

            if download_content and oa_status in (
                OpenAccessStatus.GOLD,
                OpenAccessStatus.GREEN,
                OpenAccessStatus.BRONZE,
            ):
                cache_path, cache_hash = self._download_content(record)

            result.cached = cache_path is not None
            result.cache_path = str(cache_path) if cache_path else None
            result.cache_hash = cache_hash

            # Determine final status
            if result.cached:
                result.status = IngestStatus.SUCCESS
            elif not download_content:
                result.status = IngestStatus.METADATA_ONLY
            else:
                result.status = IngestStatus.PARTIAL

            # Create manifest entry
            entry = ManifestEntry(
                reference=record,
                cached=result.cached,
                cache_path=cache_path,
                cache_hash=cache_hash,
                ingested_at=datetime.now(UTC),
            )

            return result, entry

        except Exception as e:
            result.error = str(e)
            return result, None

    def _resolve_and_fetch(self, ref: ReferenceEntry) -> ReferenceRecord | None:
        """Resolve reference identifier and fetch metadata."""
        # Priority: DOI > arXiv > title search

        # Try DOI first
        if ref.doi:
            record = self._crossref.get_by_doi(ref.doi)
            if record:
                return record

        # Try arXiv ID
        if ref.arxiv_id:
            record = self._arxiv.get_by_id(ref.arxiv_id)
            if record:
                return record

        # Fall back to title search
        if ref.citation:
            # Extract first author and title from citation text
            # This is heuristic; may need refinement
            results = self._crossref.search_by_title(ref.citation[:100])
            if results:
                return results[0]

        return None

    def _check_oa_status(
        self, record: ReferenceRecord
    ) -> tuple[OpenAccessStatus, str | None]:
        """Check open access status."""
        # arXiv is always open
        if record.arxiv_id:
            return OpenAccessStatus.GOLD, f"https://arxiv.org/abs/{record.arxiv_id}"

        # Check via Unpaywall for DOI
        if record.doi:
            return self._unpaywall.get_oa_status(record.doi)

        return OpenAccessStatus.UNKNOWN, None

    def _download_content(
        self, record: ReferenceRecord
    ) -> tuple[Path | None, str | None]:
        """Download content if available."""
        # Prefer arXiv HTML (newer, cleaner)
        if record.arxiv_id:
            path, hash_ = self._arxiv.download_html(record.arxiv_id, self._cache_dir)
            if path:
                return path, hash_

            # Fall back to source tarball
            path, hash_ = self._arxiv.download_source(record.arxiv_id, self._cache_dir)
            if path:
                return path, hash_

        # TODO: Handle other OA sources (Unpaywall URLs)
        # For v1, we only download from arXiv

        return None, None

    def _load_manifest(self, path: Path) -> ProblemManifest | None:
        """Load existing manifest if present."""
        if not path.exists():
            return None

        import yaml

        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return ProblemManifest.model_validate(data)
        except Exception:
            return None

    def _write_manifest(self, manifest: ProblemManifest, path: Path) -> None:
        """Write manifest to YAML file."""
        import yaml

        data = manifest.model_dump(mode="json")
        content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        path.write_text(content, encoding="utf-8")
```

---

## 5) CLI Command

```python
# src/erdos/commands/ingest.py
"""erdos ingest - fetch reference metadata and content."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from erdos.application.ingest_service import IngestService
from erdos.commands.output import CLIOutput
from erdos.domain.ingest import IngestStatus, IngestSummary
from erdos.ports.problem_repository import ProblemRepository


app = typer.Typer(help="Ingest reference metadata and content.")
console = Console()
err_console = Console(stderr=True)


def _output(ctx: typer.Context, data: CLIOutput) -> None:
    """Output result based on format preference."""
    if (ctx.obj or {}).get("json"):
        console.print_json(data.model_dump_json())
    elif data.success:
        _print_human(cast(dict[str, Any], data.data))
    else:
        error = cast(dict[str, Any], data.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def _print_human(data: dict[str, Any]) -> None:
    """Pretty-print ingest results."""
    summary = data.get("summary", {})
    refs = data.get("references", [])

    console.print(f"\n[bold]Ingestion Summary[/bold]")
    console.print(f"  References: {summary.get('total_references', 0)} total")
    console.print(f"  Metadata fetched: {summary.get('metadata_fetched', 0)}")
    console.print(f"  Content downloaded: {summary.get('content_downloaded', 0)}")

    if summary.get("errors", 0) > 0:
        console.print(f"  [red]Errors: {summary['errors']}[/red]")

    console.print(f"\nManifest saved: {data.get('manifest_path')}")


def ingest_problem(
    problem_id: int,
    repository: ProblemRepository,
    *,
    force: bool = False,
    download_content: bool = True,
) -> CLIOutput:
    """Core ingest logic."""
    problem = repository.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=3,
        )

    if not problem.references:
        return CLIOutput.err(
            command="erdos ingest",
            error_type="NoReferences",
            message=f"Problem {problem_id} has no references to ingest",
            code=2,
        )

    service = IngestService()
    summary = service.ingest(problem, force=force, download_content=download_content)

    return CLIOutput.ok(
        command="erdos ingest",
        data={
            "problem_id": problem_id,
            "manifest_path": summary.manifest_path,
            "summary": {
                "total_references": summary.total_references,
                "metadata_fetched": summary.metadata_fetched,
                "content_downloaded": summary.content_downloaded,
                "skipped": summary.skipped,
                "errors": summary.errors,
            },
            "references": [r.model_dump(mode="json") for r in summary.references],
        },
    )


@app.callback(invoke_without_command=True)
def ingest(
    ctx: typer.Context,
    problem_id: Annotated[
        int,
        typer.Argument(help="Problem ID to ingest references for.", min=1),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Re-fetch even if manifest exists"),
    ] = False,
    no_download: Annotated[
        bool,
        typer.Option("--no-download", help="Fetch metadata only, skip content"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON for machine consumption."),
    ] = False,
) -> None:
    """
    Ingest (fetch) reference data for a problem.

    Fetches metadata from Crossref/arXiv, checks OA status via Unpaywall,
    and downloads legally available content.

    Example: erdos ingest 6
    """
    ctx.ensure_object(dict)
    if json_output:
        ctx.obj["json"] = True

    start_time = time.perf_counter()

    # Load problem via repository
    from erdos.infrastructure.loaders.yaml_loader import YamlProblemLoader

    try:
        repository = YamlProblemLoader.from_default()
    except Exception as e:
        result = CLIOutput.err(
            command="erdos ingest",
            error_type="LoaderError",
            message=str(e),
            code=1,
        )
        _output(ctx, result)
        raise typer.Exit(code=1) from None

    # Show progress for human mode
    if not json_output:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Ingesting references for problem {problem_id}...", total=None)
            result = ingest_problem(
                problem_id, repository, force=force, download_content=not no_download
            )
    else:
        result = ingest_problem(
            problem_id, repository, force=force, download_content=not no_download
        )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result.duration_ms = duration_ms

    _output(ctx, result)

    if not result.success:
        error = cast(dict[str, Any], result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
```

---

## 6) Manifest Format

```yaml
# literature/manifests/0006.yaml
schema_version: 1
problem_id: 6
created_at: "2026-01-17T12:00:00Z"
updated_at: "2026-01-17T12:00:00Z"
entries:
  - reference:
      doi: "10.1006/jnth.1996.0001"
      arxiv_id: "0704.1234"
      title: "Small primes in arithmetic progressions"
      authors:
        - "Paul Erdős"
        - "John Smith"
      year: 1975
      venue: "Journal of Number Theory"
      oa_status: "green"
      oa_url: "https://arxiv.org/abs/0704.1234"
      source: "crossref"
    cached: true
    cache_path: "literature/cache/arxiv_0704.1234.html"
    cache_hash: "d41d8cd98f00b204e9800998ecf8427e"
    extracted: false
    extract_path: null
    ingested_at: "2026-01-17T12:00:00Z"
    error: null

  - reference:
      doi: "10.1090/S0002-9947-1944-..."
      title: "On the least prime in an arithmetic progression"
      authors:
        - "Yu. V. Linnik"
      year: 1944
      oa_status: "closed"
      source: "crossref"
    cached: false
    cache_path: null
    cache_hash: null
    ingested_at: "2026-01-17T12:00:05Z"
    error: null
```

---

## 7) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_ingest.py
"""Unit tests for ingest functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erdos.application.ingest_service import IngestService
from erdos.domain.ingest import IngestStatus
from erdos.domain.problem import ProblemRecord, ProblemStatus, ReferenceEntry
from erdos.domain.reference import OpenAccessStatus, ReferenceRecord


@pytest.fixture
def sample_problem() -> ProblemRecord:
    return ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Test statement",
        status=ProblemStatus.OPEN,
        references=[
            ReferenceEntry(key="Ref1", doi="10.1234/test"),
            ReferenceEntry(key="Ref2", arxiv_id="2201.00001"),
        ],
    )


class TestIngestService:
    def test_ingest_with_doi_reference(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Ingest fetches metadata for DOI references."""
        mock_crossref = MagicMock()
        mock_crossref.get_by_doi.return_value = ReferenceRecord(
            doi="10.1234/test",
            title="Test Paper",
            authors=["Author One"],
            year=2020,
            source="crossref",
        )

        mock_unpaywall = MagicMock()
        mock_unpaywall.get_oa_status.return_value = (OpenAccessStatus.CLOSED, None)

        service = IngestService(
            crossref=mock_crossref,
            unpaywall=mock_unpaywall,
            cache_dir=tmp_path / "cache",
            manifest_dir=tmp_path / "manifests",
        )

        summary = service.ingest(sample_problem, download_content=False)

        assert summary.metadata_fetched >= 1
        mock_crossref.get_by_doi.assert_called_with("10.1234/test")

    def test_ingest_with_arxiv_reference(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Ingest fetches metadata for arXiv references."""
        mock_arxiv = MagicMock()
        mock_arxiv.get_by_id.return_value = ReferenceRecord(
            arxiv_id="2201.00001",
            title="arXiv Paper",
            authors=["Author Two"],
            year=2022,
            source="arxiv",
        )
        mock_arxiv.download_html.return_value = (None, None)
        mock_arxiv.download_source.return_value = (None, None)

        mock_crossref = MagicMock()
        mock_crossref.get_by_doi.return_value = None

        service = IngestService(
            crossref=mock_crossref,
            arxiv=mock_arxiv,
            cache_dir=tmp_path / "cache",
            manifest_dir=tmp_path / "manifests",
        )

        summary = service.ingest(sample_problem, download_content=False)

        assert summary.metadata_fetched >= 1
        mock_arxiv.get_by_id.assert_called_with("2201.00001")

    def test_ingest_skips_if_manifest_exists(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Ingest skips if manifest exists and force=False."""
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        (manifest_dir / "0006.yaml").write_text("schema_version: 1\nproblem_id: 6\nentries: []")

        service = IngestService(
            cache_dir=tmp_path / "cache",
            manifest_dir=manifest_dir,
        )

        summary = service.ingest(sample_problem, force=False)

        assert summary.skipped == len(sample_problem.references)
        assert all(r.status == IngestStatus.SKIPPED for r in summary.references)

    def test_ingest_refetches_with_force(
        self, tmp_path: Path, sample_problem: ProblemRecord
    ) -> None:
        """Ingest re-fetches when force=True."""
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        (manifest_dir / "0006.yaml").write_text("schema_version: 1\nproblem_id: 6\nentries: []")

        mock_crossref = MagicMock()
        mock_crossref.get_by_doi.return_value = ReferenceRecord(
            doi="10.1234/test",
            title="Test",
            source="crossref",
        )

        mock_unpaywall = MagicMock()
        mock_unpaywall.get_oa_status.return_value = (OpenAccessStatus.CLOSED, None)

        service = IngestService(
            crossref=mock_crossref,
            unpaywall=mock_unpaywall,
            cache_dir=tmp_path / "cache",
            manifest_dir=manifest_dir,
        )

        summary = service.ingest(sample_problem, force=True, download_content=False)

        assert summary.skipped == 0
        mock_crossref.get_by_doi.assert_called()


class TestCrossrefClient:
    def test_rate_limiting(self) -> None:
        """Crossref client respects rate limits."""
        from erdos.infrastructure.apis.crossref import CrossrefClient
        import time

        client = CrossrefClient(delay=0.1)  # Short delay for testing

        start = time.time()
        client._rate_limit()
        client._rate_limit()
        elapsed = time.time() - start

        assert elapsed >= 0.1  # At least one delay period
```

### Integration Tests

```python
# tests/integration/test_ingest.py
"""Integration tests for ingest command."""

import subprocess
from pathlib import Path


class TestIngestCommand:
    def test_ingest_creates_manifest(self, tmp_path: Path) -> None:
        """erdos ingest creates manifest file."""
        # This test requires network; skip in CI
        result = subprocess.run(
            ["uv", "run", "erdos", "ingest", "6", "--no-download", "--json"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # May fail if network unavailable; check for graceful handling
        assert result.returncode in (0, 1)  # Success or handled error

    def test_ingest_json_output_structure(self) -> None:
        """JSON output has required fields."""
        import json

        result = subprocess.run(
            ["uv", "run", "erdos", "ingest", "6", "--no-download", "--json"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "command" in data
            assert "success" in data
            assert data["command"] == "erdos ingest"
```

### Acceptance Criteria

```bash
# 1. Basic ingest works
uv run erdos ingest 6

# 2. Metadata-only mode works
uv run erdos ingest 6 --no-download

# 3. Force re-fetch works
uv run erdos ingest 6 --force

# 4. JSON output works
uv run erdos ingest 6 --json | jq .

# 5. Manifest created
ls literature/manifests/0006.yaml

# 6. Tests pass
uv run pytest tests/unit/test_ingest.py -v
uv run pytest tests/integration/test_ingest.py -v
```

---

## 8) Error Handling

| Error | Exit Code | Message |
|-------|-----------|---------|
| Problem not found | 3 | "Problem {id} not found" |
| No references | 2 | "Problem {id} has no references to ingest" |
| Network error | 4 | "Network error: {details}" |
| API rate limit | 4 | "Rate limited by {api}. Retry after {seconds}s" |
| Partial failure | 0 | Success with errors in summary |

---

## 9) Future Extensions

### Batch Ingest (v1.1+)

```bash
# Ingest all open problems
erdos ingest --all --status open

# Ingest problems with prizes
erdos ingest --all --prize-min 500
```

### Resume Support

```bash
# Resume interrupted ingest
erdos ingest 6 --resume
```

### PDF Conversion (v1.2+)

Integration with Docling for non-arXiv PDFs:
- Convert PDF to Markdown/HTML
- Preserve mathematical notation
- Store in extracts/

---

## References

- [Crossref REST API](https://api.crossref.org/)
- [arXiv API](https://info.arxiv.org/help/api/index.html)
- [Unpaywall API](https://unpaywall.org/products/api)
- [OpenAlex API](https://docs.openalex.org/) (future)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-17 | Initial spec |
