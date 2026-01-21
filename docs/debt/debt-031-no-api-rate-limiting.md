# Technical Debt 031: No Rate Limiting in API Clients

**Date:** 2026-01-21
**Status:** Open
**Priority:** P2 (API terms violation risk)
**Impact:** Batch operations could get rate-limited or blocked by external APIs

## Summary

Neither the arXiv nor Crossref API clients implement rate limiting, despite:

1. `constants.py:33` defining `API_RATE_LIMIT_DELAY = 3.0` (unused)
2. Crossref API documentation explicitly requesting rate limiting
3. arXiv API requesting polite pool behavior

## Evidence

### Unused Constant

```python
# constants.py:33
API_RATE_LIMIT_DELAY = 3.0  # seconds between API requests
```

This constant is defined but never imported or used.

### No Delay Between Requests

```python
# crossref_client.py - no delay
def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    response = requests.get(url, ...)  # Immediate request
    return response.json()

# arxiv_client.py - no delay
def fetch_arxiv_atom(arxiv_ids: list[str], ...) -> str:
    response = requests.get(url, ...)  # Immediate request
    return response.text
```

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

1. Implement rate limiting using `API_RATE_LIMIT_DELAY`
2. Add backoff on 429 responses
3. Consider using a session-level rate limiter for batch operations
4. CI still passes (`make ci`)

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

- DEBT-029: HTTP responses not closed with context managers
- DEBT-030: No retry logic for transient network failures
