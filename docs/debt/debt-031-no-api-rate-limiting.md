# Technical Debt 031: Rate Limiting Is Not Centralized (Constant Unused)

**Date:** 2026-01-21
**Status:** Open
**Priority:** P3 (Ergonomics / defaults drift)
**Impact:** Batch operations could get rate-limited or blocked by external APIs

## Summary

Batch ingestion does include a configurable delay between references, but rate limiting is not centralized:

1. `API_RATE_LIMIT_DELAY` exists in `src/erdos/core/constants.py` but is not used as the default.
2. The delay is applied between references (not per API request), so a DOI+arXiv lookup for a single reference can still make back-to-back requests.
3. The low-level API client functions (`fetch_crossref_work`, `fetch_arxiv_atom`) do not enforce throttling if called directly.

## Evidence

### Unused Constant

```python
# constants.py:33
API_RATE_LIMIT_DELAY = 3.0  # seconds between API requests
```

This constant is defined but never imported or used.

### Ingestion Delay Exists (but is not centralized)

`src/erdos/core/ingest/fetch.py` sleeps between processing references:

```python
if delay > 0:
    time.sleep(delay)
```

The ingest CLI exposes `--delay` (default `3.0`) to control this behavior.

### Batch Ingestion Impact

When running `erdos ingest` with `--force` on many problems, each problem may trigger multiple API calls in rapid succession.

## Crossref Guidelines

From Crossref API etiquette:
- Requests should include a `mailto` parameter (implemented)
- High-volume users should implement rate limiting
- 429 responses indicate rate limiting

## arXiv Guidelines

From arXiv API documentation:
- Requests should not exceed 1 per 3 seconds
- Bulk requests should use rate limiting

## Acceptance Criteria

1. Use `API_RATE_LIMIT_DELAY` as the default for `--delay` (single source of truth).
2. Decide whether throttling should be per reference or per request (document the choice).
3. If per-request throttling is needed, implement it in the ingest layer (preferred) or in the clients.
4. CI still passes (`make ci`).

## Recommended Implementation

```python
import time
from erdos.core.constants import API_RATE_LIMIT_DELAY

_last_request_time: float = 0.0

def _rate_limit() -> None:
    """Enforce minimum delay between API requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < API_RATE_LIMIT_DELAY:
        time.sleep(API_RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.monotonic()

def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    _rate_limit()
    response = requests.get(url, ...)
    ...
```

Or use a library like `ratelimit` or `tenacity`.

## Related

- DEBT-032: HTTP responses not closed with context managers
- DEBT-033: No retry logic for transient network failures
