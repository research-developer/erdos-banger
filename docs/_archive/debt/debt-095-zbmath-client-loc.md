# DEBT-095: zbMATH Client Module LOC Violation

**Priority:** P3 (Blocked by P2 issue)
**Status:** Superseded
**Found:** 2026-01-24
**Superseded:** 2026-01-24
**Superseded By:** [DEBT-093](./debt-093-exa-client-loc.md)

## Description

The zbMATH Open API client exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/clients/zbmath.py` | 835 | 500 | +335 |

## Why This Is Superseded (Not Exempted)

The original exemption claimed "cohesion benefit outweighs the LOC cost." This was partially accurate — the zbMATH-specific code IS cohesive. But it missed the root cause: ~191 LOC of duplicated infrastructure.

### LOC Breakdown

| Category | Lines | LOC | Notes |
|----------|-------|-----|-------|
| Config (ZbMathConfig) | 48-83 | ~36 | zbMATH-specific |
| Data models (MSCCode, ZbMathEntry) | 86-307 | ~218 | Complex API response parsing |
| Extract functions (_extract_*) | 115-193 | ~79 | 6 functions for complex parsing |
| Client init + ID normalization | 310-366 | ~57 | zbMATH-specific |
| **Caching logic** | 368-464 | **~97** | **Duplicated from exa.py** |
| **HTTP retry logic** | 477-570 | **~94** | **Duplicated from exa.py** |
| API methods (4 endpoints) | 572-834 | ~263 | zbMATH-specific |
| **zbMATH-specific subtotal** | | **~644** | Cohesive, justified |
| **Infrastructure subtotal** | | **~191** | Duplicated, extract |

### Root Cause

The LOC violation is caused by **~191 LOC of duplicated infrastructure** that is copy-pasted across three client modules. This is the same issue documented in DEBT-093.

### Better Than exa.py

Unlike exa.py, this module:

1. **Uses shared constants** (lines 30-36):
```python
from erdos.core.constants import (
    DEFAULT_HTTP_TIMEOUT,
    RETRY_BASE_DELAY,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
)
```

2. **Has proper cache validation** (lines 415-425):
```python
cached_at_raw = data.get("cached_at", 0)
try:
    cached_at = float(cached_at_raw)
except (TypeError, ValueError):
    logger.debug("Corrupt cache (invalid cached_at=%r)...", cached_at_raw)
    return None
```

This is the fix that exa.py and semantic_scholar.py are missing.

## Resolution Path

1. **Complete DEBT-093** — Extract shared `cache.py` and `http.py` modules
2. **zbmath.py refactored** — Remove ~191 LOC of duplicated infrastructure
3. **Expected result:** ~644 LOC (still ~144 over threshold)

## Post-DEBT-093 Assessment

After DEBT-093 extraction, zbmath.py will still be ~144 LOC over the 500 threshold. This remaining delta IS justifiable because:

| Component | LOC | Justification |
|-----------|-----|---------------|
| 2 data models | ~218 | MSCCode + ZbMathEntry with serialization |
| 6 extract functions | ~79 | Complex zbMATH API response parsing |
| 4 API methods | ~263 | get_by_zbl_id, get_by_doi, search_by_msc, search_by_title |
| Config + ID handling | ~93 | zbMATH-specific normalization |

The zbMATH API has the most complex response structure of the three clients (nested contributors, editorial_contributions, links arrays, MSC codes).

### Future Optimization (Optional)

If the module grows further, consider:
1. Extract `_extract_*` functions to `zbmath_parser.py` (~79 LOC)
2. Extract data models to `zbmath_models.py` (~218 LOC)

This is NOT required for DEBT-093 closure but noted for future reference.

## Why Superseded (Not a Separate Fix)

The infrastructure extraction in DEBT-093 is the single fix for all three client LOC violations:

| Module | Before | After DEBT-093 | Threshold |
|--------|--------|----------------|-----------|
| exa.py | 536 | ~360 | 500 |
| semantic_scholar.py | 699 | ~524 | 500 |
| **zbmath.py** | **835** | **~644** | **500** |

Creating separate tickets would:
- Fragment the work unnecessarily
- Risk inconsistent implementations
- Miss the DRY opportunity

## Inline Marker

The `# exempt: DEBT-095` marker should be **removed** from `zbmath.py` after DEBT-093 is completed. Until then, it remains as documentation.

## Notes

- The module DOES use shared constants (unlike exa.py) — partial credit
- The module DOES have proper cache validation (unlike exa.py and semantic_scholar.py) — this is the "best" of the three
- The remaining ~144 LOC over threshold after DEBT-093 is acceptable for a module with 4 API endpoints, 2 data models, and 6 parsing functions
- The original exemption was partially correct about cohesion but wrong to exempt the infrastructure code
