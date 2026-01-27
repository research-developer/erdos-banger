# SPEC-036: Lead Enrichment Pipeline

> Bridges the gap between discovery (Exa/zbMATH/S2) and enrichment (OpenAlex/Crossref/arXiv) to create a unified literature acquisition flow.

**Status:** Draft
**Target:** v4.2
**Prerequisites:**
- SPEC-022: MetadataProvider Orchestration (FallbackProvider)
- SPEC-024: Research Records (Leads CRUD)
- SPEC-029: Exa Research Integration

---

## 0) Problem Statement

### Current State (Disconnected)

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

**The Gap:** Discovery tools (Exa, zbMATH, S2) find papers and extract DOIs/arXiv IDs into leads. But:
1. Leads are not enriched with full metadata from OpenAlex/Crossref
2. Leads cannot be added to the literature manifest
3. `erdos ingest` only reads from `problem.references[]` in the enriched YAML

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

## 2) CLI Interface

### `erdos research lead enrich <problem_id>`

Fetch full metadata from OpenAlex/Crossref/arXiv for all leads with identifiers.

```bash
# Enrich all leads with DOI or arXiv ID
erdos research lead enrich 848

# Dry-run: show what would be fetched
erdos research lead enrich 848 --dry-run

# Force re-fetch even if already enriched
erdos research lead enrich 848 --force

# JSON output
erdos research lead enrich 848 --json
```

**Options:**
- `--dry-run`: Show leads that would be enriched without making API calls
- `--force`: Re-fetch metadata even if lead already has enriched data
- `--source [openalex|crossref|arxiv]`: Override default provider chain (default: FallbackProvider)
- `--timeout SECONDS`: HTTP timeout (default: 30)

**Behavior:**
1. Load leads from `research/problems/{problem_id:04d}/meta.yaml`
2. Filter leads with `doi` or `arxiv_id` set
3. For each lead:
   - If `doi`: call `FallbackProvider.get_by_doi()`
   - Else if `arxiv_id`: call `FallbackProvider.get_by_arxiv()`
   - Store enriched metadata in lead record (new fields: `enriched_title`, `enriched_authors`, `enriched_year`, `enriched_at`)
4. Write updated `meta.yaml`

**Output (JSON):**
```json
{
  "schema_version": 1,
  "command": "erdos research lead enrich",
  "success": true,
  "data": {
    "problem_id": 848,
    "leads_total": 5,
    "leads_with_identifiers": 3,
    "leads_enriched": 3,
    "leads_skipped": 0,
    "leads_failed": 0,
    "enriched": [
      {
        "lead_id": "lead-abc123",
        "doi": "10.1234/example",
        "title": "Original title from Exa",
        "enriched_title": "Full title from OpenAlex",
        "provider": "openalex"
      }
    ]
  }
}
```

### `erdos research lead ingest <problem_id>`

Add enriched leads to the literature manifest with deduplication.

```bash
# Add enriched leads to manifest
erdos research lead ingest 848

# Dry-run: show what would be added
erdos research lead ingest 848 --dry-run

# Skip leads without enrichment (default: warn and skip)
erdos research lead ingest 848 --require-enriched

# JSON output
erdos research lead ingest 848 --json
```

**Options:**
- `--dry-run`: Show what would be added without writing
- `--require-enriched`: Only ingest leads that have been enriched (skip others)
- `--skip-duplicates`: Silently skip duplicates (default: warn)

**Behavior:**
1. Load leads from `research/problems/{problem_id:04d}/meta.yaml`
2. Load existing manifest from `literature/manifests/{problem_id:04d}.yaml`
3. For each lead with `doi` or `arxiv_id`:
   - Check for duplicate in manifest (by DOI or arXiv ID)
   - If duplicate: skip (log warning)
   - If new: create `ManifestEntry` from lead + enriched data
4. Write updated manifest (atomic write)
5. Mark ingested leads with `ingested_at` timestamp

**Deduplication Rules:**
- Primary key: DOI (normalized to lowercase)
- Secondary key: arXiv ID (if no DOI)
- Leads without identifiers are skipped with warning

**Output (JSON):**
```json
{
  "schema_version": 1,
  "command": "erdos research lead ingest",
  "success": true,
  "data": {
    "problem_id": 848,
    "leads_total": 5,
    "leads_ingested": 2,
    "leads_skipped_no_id": 1,
    "leads_skipped_duplicate": 1,
    "leads_skipped_not_enriched": 1,
    "manifest_path": "literature/manifests/0848.yaml",
    "manifest_entries_before": 0,
    "manifest_entries_after": 2
  }
}
```

---

## 3) Data Model Changes

### Lead Record Extensions

Add new fields to `LeadRecord` in `src/erdos/core/research/models.py`:

```python
class LeadRecord(BaseModel):
    # Existing fields
    id: str
    title: str
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    status: LeadStatus = LeadStatus.NEW
    priority: Priority = Priority.MEDIUM
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # NEW: Enrichment fields
    enriched_title: str | None = None
    enriched_authors: list[str] | None = None
    enriched_year: int | None = None
    enriched_venue: str | None = None
    enriched_abstract: str | None = None
    enriched_provider: str | None = None  # "openalex", "crossref", "arxiv"
    enriched_at: datetime | None = None

    # NEW: Ingest tracking
    ingested_at: datetime | None = None
    manifest_entry_id: str | None = None  # Reference to ManifestEntry
```

### Manifest Entry Source Tracking

Add provenance field to `ManifestEntry`:

```python
class ManifestEntry(BaseModel):
    # Existing fields...

    # NEW: Source tracking
    source: Literal["problem_ref", "lead"] = "problem_ref"
    lead_id: str | None = None  # If source == "lead"
```

---

## 4) Implementation

### 4.1 `src/erdos/core/research/enrichment.py` (NEW)

```python
"""Lead enrichment service using FallbackProvider."""

from erdos.core.providers.fallback import FallbackProvider
from erdos.core.research.models import LeadRecord
from erdos.core.models import ReferenceRecord

class LeadEnrichmentService:
    """Enriches leads with full metadata from OpenAlex/Crossref/arXiv."""

    def __init__(self, provider: FallbackProvider):
        self.provider = provider

    def enrich_lead(self, lead: LeadRecord) -> tuple[LeadRecord, ReferenceRecord | None]:
        """Enrich a single lead with metadata.

        Returns:
            Tuple of (updated lead, reference record or None if not found)
        """
        ref: ReferenceRecord | None = None

        if lead.doi:
            ref = self.provider.get_by_doi(lead.doi)
        elif lead.arxiv_id:
            ref = self.provider.get_by_arxiv(lead.arxiv_id)

        if ref:
            lead = lead.model_copy(update={
                "enriched_title": ref.title,
                "enriched_authors": ref.authors,
                "enriched_year": ref.year,
                "enriched_venue": ref.venue,
                "enriched_abstract": ref.abstract,
                "enriched_provider": ref.source,
                "enriched_at": datetime.now(UTC),
            })

        return lead, ref
```

### 4.2 `src/erdos/core/research/manifest_bridge.py` (NEW)

```python
"""Bridge between research leads and literature manifests."""

from erdos.core.ingest.models import ManifestEntry, ProblemManifest
from erdos.core.research.models import LeadRecord

class ManifestBridge:
    """Converts enriched leads to manifest entries with deduplication."""

    def __init__(self, manifest: ProblemManifest):
        self.manifest = manifest
        self._doi_index = self._build_doi_index()
        self._arxiv_index = self._build_arxiv_index()

    def _build_doi_index(self) -> set[str]:
        return {e.doi.lower() for e in self.manifest.entries if e.doi}

    def _build_arxiv_index(self) -> set[str]:
        return {e.arxiv_id for e in self.manifest.entries if e.arxiv_id}

    def is_duplicate(self, lead: LeadRecord) -> bool:
        """Check if lead already exists in manifest."""
        if lead.doi and lead.doi.lower() in self._doi_index:
            return True
        if lead.arxiv_id and lead.arxiv_id in self._arxiv_index:
            return True
        return False

    def lead_to_entry(self, lead: LeadRecord) -> ManifestEntry:
        """Convert enriched lead to manifest entry."""
        return ManifestEntry(
            doi=lead.doi,
            arxiv_id=lead.arxiv_id,
            title=lead.enriched_title or lead.title,
            authors=lead.enriched_authors or [],
            year=lead.enriched_year,
            venue=lead.enriched_venue,
            abstract=lead.enriched_abstract,
            source="lead",
            lead_id=lead.id,
        )
```

### 4.3 Command Implementations

- `src/erdos/commands/research/lead_enrich.py` (NEW)
- `src/erdos/commands/research/lead_ingest.py` (NEW)

Both follow existing patterns from `src/erdos/commands/research/` with:
- AppContext for dependency injection
- CLIOutput for structured responses
- Rich console for human-readable output

---

## 5) Integration Points

### With Existing Commands

| Command | Integration |
|---------|-------------|
| `erdos research exa search --save-leads` | Feeds leads with DOI/arXiv IDs |
| `erdos refs zbmath` | User can manually add results as leads |
| `erdos refs s2` | User can manually add results as leads |
| `erdos ingest` | Continues to work for `problem.references[]` |
| `erdos search` | Manifest entries are indexed as before |

### With FallbackProvider (SPEC-022)

Reuses the existing provider chain:
- DOI chain: OpenAlex → Crossref
- arXiv chain: OpenAlex → arXiv

No changes to provider architecture needed.

---

## 6) Verification

### Unit Tests

```python
# tests/unit/core/research/test_enrichment.py
def test_enrich_lead_with_doi():
    """Lead with DOI is enriched via FallbackProvider."""

def test_enrich_lead_with_arxiv():
    """Lead with arXiv ID is enriched via FallbackProvider."""

def test_enrich_lead_no_identifier():
    """Lead without identifiers returns None."""

# tests/unit/core/research/test_manifest_bridge.py
def test_duplicate_detection_by_doi():
    """Duplicate DOIs are detected."""

def test_duplicate_detection_by_arxiv():
    """Duplicate arXiv IDs are detected."""

def test_lead_to_entry_conversion():
    """Enriched lead converts to ManifestEntry correctly."""
```

### Integration Tests

```python
# tests/integration/test_lead_enrichment.py
def test_enrich_and_ingest_workflow():
    """Full workflow: add lead → enrich → ingest → verify manifest."""

def test_deduplication_across_ingests():
    """Second ingest skips duplicates."""
```

### CLI Tests

```bash
# Dry-run should not modify files
erdos research lead enrich 848 --dry-run
erdos research lead ingest 848 --dry-run

# JSON output is valid
erdos research lead enrich 848 --json | jq .
erdos research lead ingest 848 --json | jq .
```

### Acceptance Criteria

```bash
# Full workflow test
uv run erdos research exa search 848 "squarefree" --save-leads
uv run erdos research lead enrich 848
uv run erdos research lead ingest 848
uv run erdos refs problem 848  # Should show new entries
```

---

## 7) Migration & Backwards Compatibility

### No Breaking Changes

- Existing `erdos ingest` behavior unchanged
- Existing lead records remain valid (new fields are optional)
- Existing manifests remain valid (new fields are optional)

### Migration

None required. New fields have defaults.

---

## 8) Error Handling

| Scenario | Behavior |
|----------|----------|
| Lead has no DOI or arXiv ID | Skip with warning, continue |
| Provider returns None | Mark as "not found", continue |
| Provider network error | Log error, continue with other leads |
| All providers fail | Return partial success with error details |
| Manifest write fails | Rollback, return error |

---

## 9) Future Extensions

1. **Auto-enrich on save**: `--save-leads --enrich` flag for Exa search
2. **Batch discovery → ingest**: `erdos research discover 848 --query "..." --ingest`
3. **Cross-problem deduplication**: Global reference store
4. **Citation chain following**: Enrich → get citations → add as leads → recurse

---

## 10) Related

- Issue #34: Lead enrichment pipeline (tracks this work)
- SPEC-022: MetadataProvider Orchestration (provides FallbackProvider)
- SPEC-024: Research Records (provides LeadRecord)
- SPEC-029: Exa Research Integration (provides discovery → leads)
- `master-vision.md` Section 7: API Orchestration Strategy

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-26 | Initial draft |
