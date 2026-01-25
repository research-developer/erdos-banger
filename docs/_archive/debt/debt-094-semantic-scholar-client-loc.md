# DEBT-094: Semantic Scholar Client Module LOC Violation

**Priority:** P3 (Blocked by P2 issue)
**Status:** Superseded
**Found:** 2026-01-24
**Superseded:** 2026-01-24
**Superseded By:** [DEBT-093](./debt-093-exa-client-loc.md)

## Description

The Semantic Scholar API client exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/clients/semantic_scholar.py` | 699 | 500 | +199 |

## Why This Is Superseded (Not Exempted)

The original exemption claimed "cohesion benefit outweighs the LOC cost." This was partially accurate but missed the root cause.

### LOC Breakdown

| Category | Lines | Notes |
|----------|-------|-------|
| Data models (S2Paper, CitationContext, S2Reference) | ~168 | S2-specific, legitimate |
| `_normalize_identifier()` | ~35 | S2-specific ID handling |
| API methods (get_paper, get_citations, get_references) | ~187 | S2-specific, legitimate |
| **S2-specific subtotal** | **~390** | Cohesive, justified |
| Caching logic | ~82 | Duplicated from exa.py |
| HTTP retry logic | ~93 | Duplicated from exa.py |
| **Infrastructure subtotal** | **~175** | Duplicated, extract |

### Root Cause

The LOC violation is caused by **~175 LOC of duplicated infrastructure** that is copy-pasted across three client modules. This is the same issue documented in DEBT-093.

### Same Bug as exa.py

The module shares the cache validation bug (line 366):

```python
# semantic_scholar.py line 366 — assumes cached_at is always a valid number
cached_at = data.get("cached_at", 0)
ttl_seconds = self.config.cache_ttl_days * 24 * 60 * 60
if time.time() - cached_at > ttl_seconds:
```

This will be fixed by DEBT-093's shared `FileCache` module.

### Better Than exa.py

Unlike exa.py, this module correctly uses shared constants (lines 24-30):

```python
from erdos.core.constants import (
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
)
```

## Resolution Path

1. **Complete DEBT-093** — Extract shared `cache.py` and `http.py` modules
2. **semantic_scholar.py refactored** — Remove ~175 LOC of duplicated infrastructure
3. **Expected result:** ~524 LOC (within acceptable tolerance for a module with 3 data models + 3 API methods)

## Why Superseded (Not a Separate Fix)

The infrastructure extraction in DEBT-093 is the single fix for all three client LOC violations:

| Module | Before | After DEBT-093 | Threshold |
|--------|--------|----------------|-----------|
| exa.py | 536 | ~360 | 500 |
| **semantic_scholar.py** | **699** | **~524** | **500** |
| zbmath.py | 834 | ~550 | 500 |

Creating separate tickets would:
- Fragment the work unnecessarily
- Risk inconsistent implementations
- Miss the DRY opportunity

## Inline Marker

The `# exempt: DEBT-094` marker should be **removed** from `semantic_scholar.py` after DEBT-093 is completed. Until then, it remains as documentation.

## Notes

- The remaining ~24 LOC over threshold is acceptable for a module with 3 API endpoints and 3 data models
- The module IS cohesive for its S2-specific code; the exemption was partially correct
- The error was claiming cohesion for the infrastructure code, which is NOT S2-specific
