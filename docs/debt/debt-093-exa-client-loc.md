# DEBT-093: Exa Client Infrastructure Duplication

**Priority:** P2 (Material quality gap)
**Status:** Open
**Found:** 2026-01-24
**Re-specified:** 2026-01-24

## Description

The Exa client module (`src/erdos/core/clients/exa.py`, 536 LOC) exceeds the 500 LOC threshold by 36 lines. More importantly, it contains **duplicated infrastructure code** that is copy-pasted across three client modules (exa.py, semantic_scholar.py, zbmath.py).

### Previous Assessment (Incorrect)

The original debt document claimed:
> "The module is cohesive: all types and functions support a single capability (Exa API integration). The marginal violation (+41 LOC) doesn't justify splitting."

This was **reward hacking**. The module contains two types of code:
1. **API-specific logic** (high cohesion, should stay) — response parsing, URL extraction, data models
2. **Generic infrastructure** (low cohesion, should extract) — caching, HTTP retry, config patterns

The infrastructure code is duplicated verbatim across all three clients.

## Evidence of Duplication

### 1. Caching Logic (~78 LOC duplicated)

| Function | exa.py | semantic_scholar.py | zbmath.py |
|----------|--------|---------------------|-----------|
| `_cache_key()` | L227-238 | L321-332 | L368-381 |
| `get_cache_path()` | L240-251 | L347-358 | L383-394 |
| `_load_from_cache()` | L253-285 | L347-379 | L396-438 |
| `_save_to_cache()` | L287-307 | L381-405 | L440-471 |

All three use identical patterns:
- SHA256 hash of normalized key
- JSON file storage with `cached_at` timestamp
- TTL expiry check

### 2. HTTP Retry Logic (~103 LOC duplicated)

| Function | exa.py | semantic_scholar.py | zbmath.py |
|----------|--------|---------------------|-----------|
| `_post_with_retry()` / `_get_with_retry()` | L390-466 | L418-486 | L477-545 |
| `_get_retry_delay()` | L468-493 | L488-511 | L547-570 |

All three implement:
- Retry loop with configurable max attempts
- Exponential backoff with jitter
- Retry-After header handling for 429
- Retryable status code detection

### 3. Inconsistent Constant Usage (Bug)

**exa.py uses hardcoded values:**
```python
# exa.py line 413
retryable_codes = {429, 500, 502, 503, 504}  # HARDCODED

# exa.py line 480
max_delay = 30.0  # HARDCODED

# exa.py line 492
delay = 2.0 * (2**attempt)  # HARDCODED base
```

**semantic_scholar.py and zbmath.py use shared constants:**
```python
from erdos.core.constants import (
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRYABLE_STATUS_CODES,
)
```

This is evidence of **copy-paste evolution** — later clients improved on the pattern but exa.py wasn't updated.

### 4. Missing Error Handling (Bug)

**exa.py has no validation for corrupt `cached_at`:**
```python
# exa.py line 274 — assumes cached_at is always a valid number
cached_at = data.get("cached_at", 0)
ttl_seconds = self.config.cache_ttl_hours * 60 * 60
if time.time() - cached_at > ttl_seconds:
```

**zbmath.py has proper validation:**
```python
# zbmath.py lines 416-425
cached_at_raw = data.get("cached_at", 0)
try:
    cached_at = float(cached_at_raw)
except (TypeError, ValueError):
    logger.debug("Corrupt cache (invalid cached_at=%r)...", cached_at_raw)
    return None
```

## Root Cause

The three client modules were implemented sequentially without extracting shared infrastructure. Each subsequent client copied and slightly improved the patterns from the previous one, leading to:

1. ~300 LOC of duplicated retry logic across 3 modules
2. ~240 LOC of duplicated caching logic across 3 modules
3. Inconsistent bug fixes (zbmath has fixes that exa doesn't)
4. Maintenance burden when patterns need updating

## Acceptance Criteria

### Phase 1: Extract Shared Infrastructure

1. **Create `src/erdos/core/clients/cache.py`** (~80 LOC)
   - Generic `FileCache` class with SHA256 key generation
   - TTL-based expiry with robust `cached_at` validation
   - JSON serialization with error handling
   - Configurable cache path and TTL

2. **Create `src/erdos/core/clients/http.py`** (~60 LOC)
   - Generic `RetryingHTTPClient` or `retry_request()` function
   - Uses shared constants: `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`, `RETRYABLE_STATUS_CODES`
   - Supports both GET and POST
   - Handles Retry-After header

### Phase 2: Refactor exa.py

3. **Use shared `FileCache`** — remove `_cache_key`, `get_cache_path`, `_load_from_cache`, `_save_to_cache`
4. **Use shared retry logic** — remove `_post_with_retry`, `_get_retry_delay`
5. **Fix hardcoded constants** — use `RETRYABLE_STATUS_CODES`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`

### Phase 3: Refactor semantic_scholar.py and zbmath.py

6. Apply same extraction to bring all three clients under LOC threshold

## Expected Outcome

| Module | Before | After | Change |
|--------|--------|-------|--------|
| `clients/cache.py` | 0 | ~80 | new |
| `clients/http.py` | 0 | ~60 | new |
| `exa.py` | 536 | ~360 | -176 |
| `semantic_scholar.py` | 699 | ~500 | -199 |
| `zbmath.py` | 834 | ~550 | -284 |
| **Total** | 2,069 | ~1,550 | **-519** |

All three clients would be at or under the 500 LOC threshold, with shared infrastructure properly abstracted.

## Why P2 (Not P4)

1. **DRY violation** — 540 LOC of duplicated code is a material quality gap
2. **Inconsistent behavior** — exa.py has bugs that zbmath.py fixed
3. **Maintenance burden** — any fix to retry/cache logic must be applied 3 times
4. **Blocks future work** — adding new clients requires copy-pasting ~180 LOC

## Notes

- The original exemption claimed "cohesion benefit outweighs LOC cost" — this was incorrect
- Infrastructure code (caching, retry) has LOW cohesion with API-specific code
- Extracting shared code IMPROVES cohesion by grouping similar concerns
