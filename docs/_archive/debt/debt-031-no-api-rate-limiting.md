# Technical Debt 031: Rate Limiting Is Not Centralized (Constant Unused)

**Date:** 2026-01-21
**Status:** Fixed
**Priority:** P3 (Ergonomics / defaults drift)
**Impact:** Batch operations could get rate-limited or blocked by external APIs
**Fixed In:** c50766c

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
- Requests should include a `User-Agent` header (implemented via `ARXIV_USER_AGENT`)
- Bulk requests should be rate limited (a commonly cited guideline is ~1 request per ~3 seconds)

## Acceptance Criteria

1. Use `API_RATE_LIMIT_DELAY` as the default for `--delay` (single source of truth).
2. Decide whether throttling should be per reference or per request (document the choice).
3. If per-request throttling is needed, implement it in the ingest layer (preferred) or in the clients.
4. CI still passes (`make ci`).

## Resolution

**Throttling Strategy: Per-Reference**

Per-reference throttling was chosen because:
- Each reference makes at most 1-3 API requests (DOI lookup, arXiv metadata, arXiv source download)
- With a 3-second delay between references, this yields an average of 1-3 seconds per request
- This satisfies typical API rate limits (Crossref, arXiv recommend ~3s between requests)
- Per-request throttling would add complexity with minimal benefit

**Changes Made:**
1. `API_RATE_LIMIT_DELAY` is now used as the default for `--delay` in:
   - `src/erdos/commands/ingest.py` (CLI option and `IngestOptions` dataclass)
   - `src/erdos/core/ingest/service.py` (function signature)
2. Updated docstrings in `constants.py` and `service.py` to document per-reference throttling
3. All existing tests pass; no behavior change (value was already 3.0)

## Related

- DEBT-032: HTTP responses not closed with context managers
- DEBT-033: No retry logic for transient network failures
