# Bug: Crossref and Semantic Scholar clients missing JSONDecodeError handling

**Priority:** P1
**Status:** Open
**Found:** 2026-01-26
**GitHub Issue:** #35

## Description

During an architectural audit (preparing SPEC-036/037), found that `crossref.py` and `semantic_scholar.py` clients call `response.json()` without catching `JSONDecodeError`. If the API returns malformed JSON (network issues, API bugs, rate limiting with HTML error page), the CLI crashes with an unhandled exception.

## Affected Files

### `src/erdos/core/clients/crossref.py:151`

```python
# Current - NO ERROR HANDLING
return response.json()  # type: ignore[no-any-return]
```

### `src/erdos/core/clients/semantic_scholar.py:307, 360, 418`

```python
# Current - catches HTTPError but not JSONDecodeError
try:
    response = fetch_with_retry(url, ...)
    data = response.json()  # Could raise JSONDecodeError
except requests.HTTPError as e:
    # Only catches HTTP errors, not JSON errors
```

## Steps to Reproduce

1. Simulate malformed JSON response from Crossref/S2 API
2. Run `erdos ingest 6 --source crossref` or `erdos refs s2 citations <doi>`
3. Observe unhandled `JSONDecodeError` exception

## Expected Behavior

Graceful error handling with structured `CLIOutput.err()` response.

## Actual Behavior

Unhandled exception crashes the CLI.

## Root Cause

Missing try/except wrapper around `response.json()` calls.

## Correct Pattern (from `exa.py:243-252`)

```python
try:
    data = response.json()
except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
    snippet = response.text[:200].replace("\n", "\\n")
    logger.error(
        "Invalid JSON for %s (status %d): %s",
        url,
        response.status_code,
        snippet,
    )
    raise
```

## Fix

Add try/except wrapping in:
- `src/erdos/core/clients/crossref.py` line 151
- `src/erdos/core/clients/semantic_scholar.py` lines 307, 360, 418

Match the pattern used in `exa.py` for consistency.

## Related

- SPEC-036: Lead Enrichment Pipeline (uses FallbackProvider which chains these clients)
- Architecture audit 2026-01-26
