# DEBT-063: `MetadataProvider` Protocol Violates Interface Segregation

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Found By:** Clean Code audit (SOLID principles review)
**Fixed In:** 8966898

---

## Summary

`MetadataProvider` protocol in `src/erdos/core/ports.py` requires all implementers to provide `get_by_doi()`, `get_by_arxiv()`, and `search()` methods. This violates Interface Segregation Principle (ISP) because:

- `ArxivProvider` implements **DOI lookup + search** but cannot fulfill them (returns `None` / `[]`)
- `CrossrefProvider` implements **arXiv lookup + search** but cannot fulfill them (returns `None` / `[]`)
- Callers often only need one lookup method

---

## Evidence

```python
# src/erdos/core/ports.py lines 23-68 (BEFORE)
class MetadataProvider(Protocol):
    def get_by_doi(self, doi: str) -> ReferenceRecord | None: ...
    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord | None: ...
    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]: ...
```

**Implementer compliance (BEFORE):**

| Provider | get_by_doi | get_by_arxiv | search |
|----------|------------|--------------|--------|
| ArxivProvider | Returns `None` (unsupported) | ✓ Implemented | Returns `[]` (unsupported) |
| CrossrefProvider | ✓ Implemented | Returns `None` (unsupported) | Returns `[]` (unsupported) |
| OpenAlexProvider | ✓ Implemented | ✓ Implemented | ✓ Implemented |
| FallbackProvider | Delegates | Delegates | Delegates |

**ISP violation**: `ArxivProvider` and `CrossrefProvider` implement methods they cannot fulfill, and the protocol does not let call sites depend on minimal capabilities.

---

## Fix Applied

1. **Split `MetadataProvider` into segregated protocols** in `ports.py`:
   - `DOILookupProvider` - providers that can resolve metadata by DOI
   - `ArxivLookupProvider` - providers that can resolve metadata by arXiv ID
   - `SearchableMetadataProvider` - providers that support text search
   - `MetadataProvider` - aggregate protocol for providers supporting all three

2. **Removed unsupported methods from providers**:
   - `ArxivProvider` now only implements `get_by_arxiv()` (no `get_by_doi`, no `search`)
   - `CrossrefProvider` now only implements `get_by_doi()` (no `get_by_arxiv`, no `search`)
   - `OpenAlexProvider` still implements all three

3. **Rewrote `FallbackProvider`** to use capability-specific chains:
   - `doi_chain: list[DOILookupProvider]` - for DOI lookups
   - `arxiv_chain: list[ArxivLookupProvider]` - for arXiv lookups
   - `search_chain: list[SearchableMetadataProvider]` - for search queries

4. **Updated wiring** in `context.py` and `ingest/fetch.py`:
   - `build_metadata_provider()` now creates: DOI: OpenAlex → Crossref, arXiv: OpenAlex → arXiv, search: OpenAlex
   - `_build_provider_from_source()` creates appropriate chains based on `MetadataSource`

**Implementer compliance (AFTER):**

| Provider | Implements |
|----------|------------|
| ArxivProvider | `ArxivLookupProvider` only |
| CrossrefProvider | `DOILookupProvider` only |
| OpenAlexProvider | All three (full `MetadataProvider`) |
| FallbackProvider | Full `MetadataProvider` via capability chains |

---

## Acceptance Criteria

1. [x] Split `MetadataProvider` into `DOILookupProvider`, `ArxivLookupProvider`, `SearchableMetadataProvider`
2. [x] `src/erdos/core/providers/arxiv.py` no longer defines `get_by_doi()` or `search()`
3. [x] `src/erdos/core/providers/crossref.py` no longer defines `get_by_arxiv()` or `search()`
4. [x] Fallback composition supports all three operations via dedicated chains (DOI/arXiv/search)
5. [x] `src/erdos/core/ingest/fetch.py` depends only on the minimal lookup protocols it needs (DOI/arXiv), not the full provider
6. [x] Call sites depend on the minimal required protocol (mypy enforces this)
7. [x] All existing tests pass
8. [x] `make ci` passes

---

## Non-Goals

- Adding new metadata providers
- Changing provider HTTP semantics (requests, parsing, retry/rate-limiting)
- Modifying CLI
