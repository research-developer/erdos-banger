# DEBT-093: Exa Client Infrastructure Duplication

**Priority:** P2 (Material quality gap)
**Status:** Resolved
**Found:** 2026-01-24
**Re-specified:** 2026-01-24
**Resolved:** 2026-01-24

## Resolution

Shared infrastructure extracted and all three clients refactored:

### New Shared Modules

1. **`src/erdos/core/clients/cache.py`** (160 LOC)
   - Generic `FileCache` class with SHA256 key generation
   - TTL-based expiry with robust `_cached_at` validation
   - JSON serialization with error handling
   - Configurable cache path and TTL
   - `make_cache_key()` helper for normalized cache key generation

2. **Extended `src/erdos/core/retry.py`** (253 LOC, +93 LOC)
   - Added `post_with_retry()` function for POST requests
   - Made `get_retry_delay()` public for testing
   - Uses shared constants: `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`, `RETRYABLE_STATUS_CODES`
   - Supports both GET and POST with Retry-After header handling

### Refactored Client LOC

| Module | Before | After | Change |
|--------|--------|-------|--------|
| `clients/cache.py` | 0 | 160 | new |
| `retry.py` | 160 | 253 | +93 |
| `exa.py` | 536 | 304 | **-232** |
| `semantic_scholar.py` | 699 | 435 | **-264** |
| `zbmath.py` | 834 | 596 | **-238** |
| **Net change** | 2,229 | 1,748 | **-481** |

All clients now use the shared `FileCache` class and `fetch_with_retry` / `post_with_retry` functions.

### Bugs Fixed

1. **Inconsistent constants** — exa.py now uses shared constants from `constants.py`
2. **Missing cache validation** — all clients use `FileCache` which validates `_cached_at` timestamp

### Remaining Work

- `zbmath.py` is at 596 LOC (96 LOC over threshold) — this is acceptable given the significant reduction and the cohesive nature of the remaining code (MSC parsing, zbMATH-specific helpers)

## Original Description

The Exa client module (`src/erdos/core/clients/exa.py`, 536 LOC) exceeded the 500 LOC threshold by 36 lines. More importantly, it contained **duplicated infrastructure code** that was copy-pasted across three client modules (exa.py, semantic_scholar.py, zbmath.py).

### Root Cause

The three client modules were implemented sequentially without extracting shared infrastructure. Each subsequent client copied and slightly improved the patterns from the previous one, leading to:

1. ~300 LOC of duplicated retry logic across 3 modules
2. ~240 LOC of duplicated caching logic across 3 modules
3. Inconsistent bug fixes (zbmath had fixes that exa didn't)
4. Maintenance burden when patterns needed updating

### Why P2 (Not P4)

1. **DRY violation** — 540 LOC of duplicated code was a material quality gap
2. **Inconsistent behavior** — exa.py had bugs that zbmath.py fixed
3. **Maintenance burden** — any fix to retry/cache logic had to be applied 3 times
4. **Blocked future work** — adding new clients required copy-pasting ~180 LOC
