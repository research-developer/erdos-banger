# SPEC-036: Lead Enrichment Pipeline

> Bridges the gap between discovery (Exa/zbMATH/S2) and enrichment (OpenAlex/Crossref/arXiv) to create a unified literature acquisition flow.

**Status:** Implementation Ready
**Target:** v4.2
**Issue:** #34
**Prerequisites:**
- SPEC-022: MetadataProvider Orchestration (FallbackProvider) ✅ IMPLEMENTED
- SPEC-024: Research Records (Leads CRUD) ✅ IMPLEMENTED
- SPEC-029: Exa Research Integration ✅ IMPLEMENTED

---

## 0) Problem Statement

### Current State (Verified 2026-01-28)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DISCOVERY (find papers)              │  ENRICHMENT (get metadata)          │
├───────────────────────────────────────┼─────────────────────────────────────┤
│  erdos research exa search            │  erdos ingest                       │
│  erdos refs zbmath                    │    └─ reads problem.references[]    │
│  erdos refs s2                        │    └─ calls FallbackProvider        │
│        ↓                              │    └─ writes manifest               │
│  research/problems/XXXX/leads         │                                     │
│  (DOI, arXiv ID captured)             │  literature/manifests/XXXX.yaml     │
│        ↓                              │                                     │
│  ❌ DEAD END                          │  ❌ ONLY FROM problem.references    │
└───────────────────────────────────────┴─────────────────────────────────────┘
```

**The Gap:** Discovery tools find papers and extract DOIs/arXiv IDs into leads. But:
1. Leads are NOT enriched with full metadata from OpenAlex/Crossref
2. Leads CANNOT be added to the literature manifest
3. `erdos ingest` ONLY reads from `problem.references[]` in the enriched YAML

**Real-world impact:** Problem #848 has `references: [{key: "Er92b", doi: null, arxiv_id: null}]`. Running `erdos ingest 848` produces an empty manifest. Meanwhile, `erdos research exa search 848 "squarefree"` finds relevant papers with DOIs, but they go nowhere.

### Proposed State (Connected)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED LITERATURE PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  DISCOVERY  │───▶│    LEADS    │───▶│  ENRICHMENT │───▶│  MANIFEST   │  │
│  │             │    │             │    │             │    │             │  │
│  │ Exa Search  │    │ DOI/arXiv   │    │ OpenAlex    │    │ Deduplicated│  │
│  │ zbMATH      │    │ extracted   │    │ Crossref    │    │ references  │  │
│  │ S2          │    │ from URLs   │    │ arXiv       │    │ with cache  │  │
│  │ Manual add  │    │             │    │ (Fallback)  │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Commands:                                                                  │
│  erdos research exa search 848 "query" --save-leads                        │
│  erdos research lead enrich 848        ← NEW                               │
│  erdos research lead ingest 848        ← NEW                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1) Scope

### In Scope (v4.2)

1. **`erdos research lead enrich <problem_id>`** - Fetch full metadata for leads with DOI/arXiv ID
2. **`erdos research lead ingest <problem_id>`** - Add enriched leads to literature manifest with deduplication
3. **Deduplication by identifier** - DOI (primary), arXiv ID (secondary)
4. **Dry-run mode** - Preview what would be added
5. **JSON output** - Machine-readable for automation

### Out of Scope

- Automatic discovery (user must run Exa/zbMATH/S2 first)
- PDF download during enrichment (handled by existing `erdos ingest --pdf`)
- Modifying `problem.references[]` in enriched YAML (manifest is the target)
- Cross-problem deduplication (per-problem manifests remain independent)

---

## 2) Tracer Bullets: What Exists vs What's Missing

### ✅ EXISTING COMPONENTS (Verified)

| Component | File | Key Elements | Lines |
|-----------|------|--------------|-------|
| **LeadRecord model** | `src/erdos/core/research/models.py` | `LeadRecord`, `LeadSource`, `LeadStatus` | 69-81 |
| **LeadSource nested** | `src/erdos/core/research/models.py` | `doi`, `arxiv_id`, `url` (all nullable) | 63-66 |
| **ManifestEntry model** | `src/erdos/core/models/reference.py` | `reference: ReferenceRecord`, `cached`, `extracted`, `ingested_at` | 113-141 |
| **ProblemManifest** | `src/erdos/core/models/reference.py` | `problem_id`, `entries: list[ManifestEntry]`, `created_at`, `updated_at` | 144-161 |
| **ReferenceRecord** | `src/erdos/core/models/reference.py` | `doi`, `arxiv_id`, `title`, `authors`, `year`, `venue`, `abstract`, `source` | 26-99 |
| **FallbackProvider** | `src/erdos/core/providers/fallback.py` | `get_by_doi(doi)`, `get_by_arxiv(arxiv_id)`, `search(query)` | 37-172 |
| **Lead CRUD** | `src/erdos/core/research/store_fs.py` | `lead_add()`, `lead_list()`, `lead_update()` | 90-199 |
| **Lead commands** | `src/erdos/commands/research/lead.py` | `add`, `list`, `update` subcommands | entire file |
| **Exa integration** | `src/erdos/commands/research/exa.py` | `--save-leads` creates leads from Exa results | 32-63 |
| **Ingest service** | `src/erdos/core/ingest/service.py` | `ingest_problem_references()` - reads `problem.references[]` only | 296-448 |
| **Atomic manifest write** | `src/erdos/core/ingest/service.py` | `_write_manifest_atomic()` | 99-121 |
| **Manifest loading** | `src/erdos/core/ingest/service.py` | `_load_existing_manifest()` | 71-96 |
| **Duplicate detection** | `src/erdos/core/ingest/service.py` | `_check_duplicate_keys()` uses stable keys | 157-176 |

### ❌ MISSING COMPONENTS (To Implement)

| Component | Target File | Purpose |
|-----------|-------------|---------|
| **Enrichment fields on LeadRecord** | `src/erdos/core/research/models.py` | `enriched_*` fields + `ingested_at` |
| **Source tracking on ManifestEntry** | `src/erdos/core/models/reference.py` | `source` + `lead_id` fields |
| **LeadEnrichmentService** | `src/erdos/core/research/enrichment.py` (NEW) | Bulk-enrich leads via FallbackProvider |
| **ManifestBridge** | `src/erdos/core/research/manifest_bridge.py` (NEW) | Dedup + conversion logic |
| **lead enrich command** | `src/erdos/commands/research/lead.py` | `enrich` subcommand |
| **lead ingest command** | `src/erdos/commands/research/lead.py` | `ingest` subcommand |
| **lead update for enrichment** | `src/erdos/core/research/store_fs.py` | Extend `lead_update()` for enrichment fields |

---

## 3) Data Model Changes

### 3.1 LeadRecord Extensions

**File:** `src/erdos/core/research/models.py`

Add to `LeadRecord` class (after line 81):

```python
# Enrichment fields (from FallbackProvider)
enriched_title: Annotated[str | None, Field(default=None)] = None
enriched_authors: Annotated[list[str] | None, Field(default=None)] = None
enriched_year: Annotated[int | None, Field(default=None)] = None
enriched_venue: Annotated[str | None, Field(default=None)] = None
enriched_abstract: Annotated[str | None, Field(default=None)] = None
enriched_provider: Annotated[str | None, Field(default=None)] = None  # "openalex", "crossref", "arxiv"
enriched_at: Annotated[datetime | None, Field(default=None)] = None

# Ingest tracking
ingested_at: Annotated[datetime | None, Field(default=None)] = None
manifest_entry_id: Annotated[str | None, Field(default=None)] = None
```

### 3.2 ManifestEntry Extensions

**File:** `src/erdos/core/models/reference.py`

Add to `ManifestEntry` class (after line 141):

```python
# Source tracking (provenance)
source: Annotated[
    Literal["problem_ref", "lead"],
    Field(default="problem_ref", description="Origin of this entry")
] = "problem_ref"
lead_id: Annotated[
    str | None,
    Field(default=None, description="LeadRecord ID if source='lead'")
] = None
```

**Import:** Add `Literal` to imports at top of file.

---

## 4) New Core Services

### 4.1 LeadEnrichmentService

**File:** `src/erdos/core/research/enrichment.py` (NEW)

```python
"""Lead enrichment service using FallbackProvider.

Bridges the gap between discovery (leads with DOI/arXiv IDs) and
enrichment (full metadata from OpenAlex/Crossref/arXiv).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erdos.core.models import ReferenceRecord
    from erdos.core.providers.fallback import FallbackProvider
    from erdos.core.research.models import LeadRecord


logger = logging.getLogger(__name__)


@dataclass
class EnrichmentStats:
    """Statistics from a batch enrichment operation."""

    total: int
    with_identifiers: int
    enriched: int
    skipped_no_id: int
    failed: int


@dataclass
class EnrichmentResult:
    """Result of enriching a single lead."""

    lead: LeadRecord
    reference: ReferenceRecord | None
    provider: str | None
    error: str | None = None


class LeadEnrichmentService:
    """Enriches leads with full metadata from OpenAlex/Crossref/arXiv."""

    def __init__(self, provider: FallbackProvider) -> None:
        self._provider = provider

    def enrich_lead(self, lead: LeadRecord) -> EnrichmentResult:
        """Enrich a single lead with metadata.

        Args:
            lead: LeadRecord with optional doi/arxiv_id in source.

        Returns:
            EnrichmentResult with updated lead and fetched reference.
        """
        # Check for identifiers in lead.source
        doi = lead.source.doi
        arxiv_id = lead.source.arxiv_id

        if not doi and not arxiv_id:
            return EnrichmentResult(lead=lead, reference=None, provider=None)

        ref: ReferenceRecord | None = None
        provider_name: str | None = None

        try:
            if doi:
                ref = self._provider.get_by_doi(doi)
            elif arxiv_id:
                ref = self._provider.get_by_arxiv(arxiv_id)

            if ref:
                provider_name = ref.source
                # Update lead with enrichment fields (using model_copy for frozen models)
                lead = lead.model_copy(update={
                    "enriched_title": ref.title,
                    "enriched_authors": list(ref.authors) if ref.authors else None,
                    "enriched_year": ref.year,
                    "enriched_venue": ref.venue,
                    "enriched_abstract": ref.abstract,
                    "enriched_provider": ref.source,
                    "enriched_at": datetime.now(UTC),
                })
                logger.info(
                    "Enriched lead %s via %s: %s",
                    lead.id,
                    provider_name,
                    ref.title[:50] if ref.title else "untitled",
                )
        except Exception as e:
            logger.warning("Failed to enrich lead %s: %s", lead.id, e)
            return EnrichmentResult(lead=lead, reference=None, provider=None, error=str(e))

        return EnrichmentResult(lead=lead, reference=ref, provider=provider_name)

    def enrich_leads(
        self, leads: list[LeadRecord], *, force: bool = False
    ) -> tuple[list[EnrichmentResult], EnrichmentStats]:
        """Enrich multiple leads.

        Args:
            leads: List of LeadRecords to enrich.
            force: If True, re-enrich even if already enriched.

        Returns:
            Tuple of (results, stats).
        """
        results: list[EnrichmentResult] = []
        enriched = 0
        skipped_no_id = 0
        failed = 0

        with_identifiers = sum(
            1 for lead in leads if lead.source.doi or lead.source.arxiv_id
        )

        for lead in leads:
            # Skip if no identifiers
            if not lead.source.doi and not lead.source.arxiv_id:
                skipped_no_id += 1
                results.append(EnrichmentResult(lead=lead, reference=None, provider=None))
                continue

            # Skip if already enriched (unless force)
            if lead.enriched_at and not force:
                results.append(EnrichmentResult(lead=lead, reference=None, provider=None))
                continue

            result = self.enrich_lead(lead)
            results.append(result)

            if result.error:
                failed += 1
            elif result.reference:
                enriched += 1

        stats = EnrichmentStats(
            total=len(leads),
            with_identifiers=with_identifiers,
            enriched=enriched,
            skipped_no_id=skipped_no_id,
            failed=failed,
        )

        return results, stats
```

### 4.2 ManifestBridge

**File:** `src/erdos/core/research/manifest_bridge.py` (NEW)

```python
"""Bridge between research leads and literature manifests.

Handles deduplication and conversion of enriched leads to manifest entries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erdos.core.models import ManifestEntry, ProblemManifest, ReferenceRecord
    from erdos.core.research.models import LeadRecord


logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    """Statistics from a batch ingest operation."""

    total: int
    ingested: int
    skipped_no_id: int
    skipped_duplicate: int
    skipped_not_enriched: int
    errors: int


class ManifestBridge:
    """Converts enriched leads to manifest entries with deduplication."""

    def __init__(self, manifest: ProblemManifest) -> None:
        self._manifest = manifest
        self._doi_index = self._build_doi_index()
        self._arxiv_index = self._build_arxiv_index()

    def _build_doi_index(self) -> set[str]:
        """Build index of existing DOIs (lowercase for case-insensitive matching)."""
        return {
            entry.reference.doi.lower()
            for entry in self._manifest.entries
            if entry.reference.doi
        }

    def _build_arxiv_index(self) -> set[str]:
        """Build index of existing arXiv IDs."""
        return {
            entry.reference.arxiv_id
            for entry in self._manifest.entries
            if entry.reference.arxiv_id
        }

    def is_duplicate(self, lead: LeadRecord) -> bool:
        """Check if lead already exists in manifest by DOI or arXiv ID."""
        if lead.source.doi and lead.source.doi.lower() in self._doi_index:
            return True
        if lead.source.arxiv_id and lead.source.arxiv_id in self._arxiv_index:
            return True
        return False

    def lead_to_entry(self, lead: LeadRecord) -> ManifestEntry:
        """Convert enriched lead to manifest entry.

        Requires lead to have enrichment data (enriched_title, etc.).
        """
        from erdos.core.models import ManifestEntry, ReferenceRecord

        # Build ReferenceRecord from enriched data
        reference = ReferenceRecord(
            doi=lead.source.doi,
            arxiv_id=lead.source.arxiv_id,
            title=lead.enriched_title or lead.title,
            authors=lead.enriched_authors or [],
            year=lead.enriched_year,
            venue=lead.enriched_venue,
            abstract=lead.enriched_abstract,
            source=lead.enriched_provider,
            fetched_at=lead.enriched_at,
        )

        # Create manifest entry with provenance
        return ManifestEntry(
            reference=reference,
            cached=False,
            extracted=False,
            ingested_at=datetime.now(UTC),
            source="lead",
            lead_id=lead.id,
        )

    def add_entry(self, entry: ManifestEntry) -> None:
        """Add entry to manifest and update indices."""
        self._manifest.entries.append(entry)
        if entry.reference.doi:
            self._doi_index.add(entry.reference.doi.lower())
        if entry.reference.arxiv_id:
            self._arxiv_index.add(entry.reference.arxiv_id)
```

---

## 5) CLI Commands

### 5.1 `erdos research lead enrich`

Add to `src/erdos/commands/research/lead.py`:

```python
@lead_app.command("enrich")
def enrich_command(
    problem_id: Annotated[int, typer.Argument(help="Problem ID")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without fetching")] = False,
    force: Annotated[bool, typer.Option("--force", help="Re-enrich even if already enriched")] = False,
    timeout: Annotated[float, typer.Option("--timeout", help="HTTP timeout")] = 30.0,
) -> None:
    """Enrich leads with full metadata from OpenAlex/Crossref/arXiv."""
    from erdos.core.research.enrichment import LeadEnrichmentService
    # ... implementation
```

### 5.2 `erdos research lead ingest`

Add to `src/erdos/commands/research/lead.py`:

```python
@lead_app.command("ingest")
def ingest_command(
    problem_id: Annotated[int, typer.Argument(help="Problem ID")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without writing")] = False,
    require_enriched: Annotated[bool, typer.Option("--require-enriched", help="Skip unenriched leads")] = False,
) -> None:
    """Add enriched leads to literature manifest with deduplication."""
    from erdos.core.research.manifest_bridge import ManifestBridge
    # ... implementation
```

---

## 6) TDD Test Plan (Uncle Bob Style)

### Phase 1: Model Tests (Red-Green-Refactor)

```python
# tests/unit/core/research/test_models_enrichment.py

def test_lead_record_has_enrichment_fields():
    """LeadRecord should have all enrichment fields with None defaults."""
    lead = LeadRecord(...)
    assert lead.enriched_title is None
    assert lead.enriched_authors is None
    assert lead.enriched_at is None
    assert lead.ingested_at is None

def test_lead_record_enrichment_fields_are_optional():
    """Existing leads without enrichment fields should still validate."""
    # Backward compatibility test

def test_manifest_entry_has_source_tracking():
    """ManifestEntry should track source and lead_id."""
    entry = ManifestEntry(...)
    assert entry.source == "problem_ref"  # default
    assert entry.lead_id is None

def test_manifest_entry_source_lead():
    """ManifestEntry should accept source='lead' with lead_id."""
    entry = ManifestEntry(..., source="lead", lead_id="lead_123")
    assert entry.source == "lead"
    assert entry.lead_id == "lead_123"
```

### Phase 2: LeadEnrichmentService Tests

```python
# tests/unit/core/research/test_enrichment.py

def test_enrich_lead_with_doi_success():
    """Lead with DOI should be enriched via FallbackProvider."""
    mock_provider = Mock()
    mock_provider.get_by_doi.return_value = ReferenceRecord(...)

    service = LeadEnrichmentService(mock_provider)
    lead = make_lead(doi="10.1234/test")
    result = service.enrich_lead(lead)

    assert result.lead.enriched_title == "..."
    assert result.lead.enriched_at is not None
    assert result.provider == "openalex"

def test_enrich_lead_with_arxiv_success():
    """Lead with arXiv ID should be enriched via FallbackProvider."""

def test_enrich_lead_no_identifier_skipped():
    """Lead without identifiers should return unchanged."""
    lead = make_lead(doi=None, arxiv_id=None)
    result = service.enrich_lead(lead)
    assert result.lead.enriched_at is None
    assert result.reference is None

def test_enrich_lead_provider_returns_none():
    """Lead with unknown identifier should remain unenriched."""

def test_enrich_lead_provider_error_handled():
    """Network errors should be caught and logged."""

def test_enrich_leads_batch_stats():
    """Batch enrichment should return accurate stats."""
```

### Phase 3: ManifestBridge Tests

```python
# tests/unit/core/research/test_manifest_bridge.py

def test_duplicate_detection_by_doi():
    """Duplicate DOIs should be detected (case-insensitive)."""
    manifest = make_manifest_with_doi("10.1234/TEST")
    bridge = ManifestBridge(manifest)
    lead = make_lead(doi="10.1234/test")  # lowercase
    assert bridge.is_duplicate(lead) is True

def test_duplicate_detection_by_arxiv():
    """Duplicate arXiv IDs should be detected."""

def test_no_duplicate_for_new_lead():
    """New leads should not be flagged as duplicates."""

def test_lead_to_entry_conversion():
    """Enriched lead should convert to ManifestEntry correctly."""
    lead = make_enriched_lead(...)
    bridge = ManifestBridge(make_empty_manifest())
    entry = bridge.lead_to_entry(lead)

    assert entry.source == "lead"
    assert entry.lead_id == lead.id
    assert entry.reference.title == lead.enriched_title

def test_add_entry_updates_indices():
    """Adding entry should update DOI and arXiv indices."""
```

### Phase 4: Integration Tests

```python
# tests/integration/test_lead_enrichment.py

@pytest.mark.requires_network
def test_enrich_and_ingest_workflow():
    """Full workflow: add lead → enrich → ingest → verify manifest."""
    # 1. Add a lead with known arXiv ID
    # 2. Run enrich
    # 3. Run ingest
    # 4. Verify manifest contains the entry

def test_deduplication_across_ingests():
    """Second ingest should skip duplicates."""
```

### Phase 5: CLI Tests

```python
# tests/unit/commands/research/test_lead_enrich_ingest.py

def test_enrich_dry_run_no_network():
    """--dry-run should not make API calls."""

def test_enrich_json_output_valid():
    """--json output should be valid CLIOutput."""

def test_ingest_dry_run_no_write():
    """--dry-run should not write manifest."""

def test_ingest_json_output_valid():
    """--json output should be valid CLIOutput."""
```

---

## 7) Implementation Order

1. **Model extensions** (LeadRecord + ManifestEntry) - enables all downstream work
2. **LeadEnrichmentService** with unit tests
3. **ManifestBridge** with unit tests
4. **FSResearchStore.lead_update()** extension for enrichment fields
5. **lead enrich command** with CLI tests
6. **lead ingest command** with CLI tests
7. **Integration tests** (requires network)
8. **Acceptance test** (full workflow)

---

## 8) Acceptance Criteria

```bash
# Full workflow test
uv run erdos research exa search 848 "squarefree" --save-leads
uv run erdos research lead enrich 848
uv run erdos research lead ingest 848
uv run erdos refs problem 848  # Should show new entries
```

- [ ] `erdos research lead enrich 848` enriches leads with full metadata
- [ ] `erdos research lead ingest 848` adds to manifest with dedup
- [ ] Existing manifest entries are preserved (merge, not overwrite)
- [ ] `--dry-run` flag shows what would be added
- [ ] `--json` output for both commands
- [ ] All unit tests pass
- [ ] Integration tests pass (with network)
- [ ] No regressions in existing tests

---

## 9) Error Handling

| Scenario | Behavior |
|----------|----------|
| Lead has no DOI or arXiv ID | Skip with warning, continue |
| Provider returns None | Mark as "not found", continue |
| Provider network error | Log error, continue with other leads |
| All providers fail | Return partial success with error details |
| Manifest write fails | Rollback, return error |

---

## 10) Related

- **Issue #34:** Lead enrichment pipeline (tracks this work)
- **BUG-039:** Ingest cannot discover papers (Phase 1 fixed, Phases 2-3 = this spec)
- **SPEC-022:** MetadataProvider Orchestration (provides FallbackProvider)
- **SPEC-024:** Research Records (provides LeadRecord)
- **SPEC-029:** Exa Research Integration (provides discovery → leads)
- `master-vision.md` Section 7: API Orchestration Strategy

---

## 11) Critical Gotchas (Verified 2026-01-28)

### 11.1 LeadRecord is Frozen (Immutable)

**Location:** `src/erdos/core/research/models.py:14-15`

```python
class _FrozenModel(ErdosBaseModel):
    model_config = ConfigDict(frozen=True)

class LeadRecord(_FrozenModel):  # Frozen!
```

**Impact:** Cannot mutate lead in-place. Must use `lead.model_copy(update={...})` pattern.

**Solution:** Already documented in spec. LeadEnrichmentService uses `model_copy()`.

### 11.2 FSResearchStore.lead_update() Only Supports 3 Fields

**Location:** `src/erdos/core/research/store_fs.py:160-194`

```python
def lead_update(
    self,
    problem_id: int,
    lead_id: str,
    *,
    status: LeadStatus | None = None,   # ✅ Supported
    priority: Priority | None = None,    # ✅ Supported
    notes: str | None = None,            # ✅ Supported
    # ❌ NO enrichment fields!
) -> tuple[LeadRecord, Path]:
```

**Impact:** Cannot use existing `lead_update()` to write enrichment fields.

**Solution:** Either:
1. **Extend `lead_update()`** to accept all enrichment fields (recommended)
2. **Add new `lead_save()`** method that writes full LeadRecord to disk
3. **Write directly** using `_write_record()` after `model_copy()`

**Recommended approach:** Add new optional parameters to `lead_update()`:

```python
def lead_update(
    self,
    problem_id: int,
    lead_id: str,
    *,
    status: LeadStatus | None = None,
    priority: Priority | None = None,
    notes: str | None = None,
    # NEW: Enrichment fields
    enriched_title: str | None = None,
    enriched_authors: list[str] | None = None,
    enriched_year: int | None = None,
    enriched_venue: str | None = None,
    enriched_abstract: str | None = None,
    enriched_provider: str | None = None,
    enriched_at: datetime | None = None,
    ingested_at: datetime | None = None,
    manifest_entry_id: str | None = None,
    now: datetime | None = None,
) -> tuple[LeadRecord, Path]:
```

### 11.3 No --dry-run in Existing Research Commands

**Location:** `src/erdos/commands/research/lead.py`

**Impact:** No existing pattern to follow for `--dry-run`.

**Solution:** Implement custom dry-run logic:

```python
if dry_run:
    # Preview mode: collect stats but don't make API calls or write files
    leads = store.lead_list(problem_id)
    with_ids = [l for l in leads if l.source.doi or l.source.arxiv_id]
    console.print(f"Would enrich {len(with_ids)} leads with identifiers")
    return
```

### 11.4 Exa Extracts Identifiers from URLs Only

**Location:** `src/erdos/core/clients/exa.py:308-323`

**Issue:** `_extract_doi()` and `_extract_arxiv_id()` only parse URLs, not page text.

```python
def _extract_doi(url: str) -> str | None:
    """Extract DOI from URL."""
    match = re.search(r"doi\.org/(.+?)(?:\?|$)", url)  # Only doi.org URLs
    ...
```

**Impact:** Semantic Scholar pages (`semanticscholar.org/paper/...`) have DOIs in page text, not URL. These won't be extracted.

**Observed:** 34 of 45 leads for Problem 74 have `source.doi: null` and `source.arxiv_id: null` because their URLs are Semantic Scholar, Springer, etc.

**Solution:** Out of scope for SPEC-036. Future enhancement: parse DOI from `relevance` field (page text).

### 11.5 Existing Manifest Entries Must Be Preserved

**Location:** `src/erdos/core/ingest/service.py:99-121`

**Issue:** Manifest writing uses `_write_manifest_atomic()` which replaces the file.

**Solution:** ManifestBridge must:
1. Load existing manifest first
2. Append new entries (not replace)
3. Use same atomic write pattern

### 11.6 Rate Limiting Between API Calls

**Location:** `src/erdos/core/ingest/fetch.py:479`

**Existing pattern:** Uses `config.fetch.delay` between references.

**Solution:** LeadEnrichmentService should accept a delay parameter and sleep between enrichment calls:

```python
import time

def enrich_leads(self, leads, *, force=False, delay: float = 1.0):
    for lead in leads:
        result = self.enrich_lead(lead)
        if delay > 0:
            time.sleep(delay)
```

---

## 12) Demo Scenario: Problem 74 (Chromatic Number)

### 12.1 Current State (Verified 2026-01-28)

**Problem 74** is the **ideal demo candidate** because:
- ✅ 45 leads already exist from Exa search
- ✅ 11 leads have arXiv IDs that can be enriched
- ✅ Existing manifest has 5 entries (good for dedup testing)
- ✅ 4 arXiv IDs overlap (tests deduplication)
- ✅ 7 unique leads can be ingested

**Lead inventory:**

| Metric | Count |
|--------|-------|
| Total leads | 45 |
| Leads with arXiv ID | 11 |
| Leads with DOI | 0 |
| Leads without identifiers | 34 |

**Manifest inventory:**

| Metric | Count |
|--------|-------|
| Existing entries | 5 |
| With arXiv ID | 4 |
| With DOI only | 1 |

**arXiv ID overlap analysis:**

```text
Manifest arXiv IDs:     Leads arXiv IDs:           Dedup?
1902.08177             1902.08177                  ⚠️ DUPLICATE
1306.5167              1306.5167                   ⚠️ DUPLICATE
2012.10409             2012.10409                  ⚠️ DUPLICATE
2203.13833             2203.13833                  ⚠️ DUPLICATE
                       2305.15585                  ✅ NEW
                       2412.09969                  ✅ NEW
                       2104.04914                  ✅ NEW
                       2506.08810                  ✅ NEW
                       2311.10379                  ✅ NEW
                       2102.05522                  ✅ NEW
                       1002.1748                   ✅ NEW
```

**Expected result after pipeline:** 7 new entries added to manifest (5 existing + 7 new = 12 total).

### 12.2 Demo Commands (Post-Implementation)

```bash
# 1. Check current state
uv run erdos research lead list 74 --json | jq '.data.records | length'
# Expected: 45

# 2. Dry-run enrichment (no API calls)
uv run erdos research lead enrich 74 --dry-run
# Expected output:
# Would enrich 11 leads with identifiers
# - 0 already enriched
# - 34 without identifiers (skipped)

# 3. Enrich leads (live API)
uv run erdos research lead enrich 74
# Expected output:
# Enriched 11 leads via OpenAlex
# - 11 successful
# - 0 failed
# - 34 skipped (no identifier)

# 4. Dry-run ingest (no file writes)
uv run erdos research lead ingest 74 --dry-run
# Expected output:
# Would add 7 entries to manifest
# - 4 duplicates skipped (already in manifest)
# - 34 skipped (no identifier)

# 5. Ingest leads to manifest
uv run erdos research lead ingest 74
# Expected output:
# Added 7 entries to literature/manifests/0074.yaml
# - 4 duplicates skipped
# - 34 skipped (no identifier)

# 6. Verify manifest
uv run erdos refs manifest 74 --json | jq '.data.entries | length'
# Expected: 12 (5 existing + 7 new)

# 7. Verify new entries have source=lead
uv run erdos refs manifest 74 --json | jq '[.data.entries[] | select(.source == "lead")] | length'
# Expected: 7
```

### 12.3 Required Environment Variables

```bash
# .env file must contain:
OPENALEX_API_KEY=...  # Optional but recommended for rate limits
ERDOS_MAILTO=...      # Required for polite pool
```

### 12.4 Demo Acceptance Criteria

- [ ] `erdos research lead enrich 74` enriches 11 leads
- [ ] `erdos research lead ingest 74` adds exactly 7 new entries
- [ ] 4 duplicate arXiv IDs are correctly skipped
- [ ] 34 leads without identifiers are skipped with warning
- [ ] New manifest entries have `source: "lead"` and `lead_id`
- [ ] Original 5 manifest entries are preserved
- [ ] `--dry-run` works correctly for both commands
- [ ] `--json` output is valid CLIOutput

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-26 | Initial draft |
| 0.2.0 | 2026-01-28 | Verified tracer bullets, added TDD plan, implementation order |
| 0.3.0 | 2026-01-28 | Added critical gotchas, demo scenario for Problem 74, FSResearchStore extension needs |
