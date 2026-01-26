# Bug: Crossref/Semantic Scholar clients missing JSONDecodeError handling

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** (in-tree)
**GitHub Issue:** [#35](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/issues/35)

## Description

During architectural audit for SPEC-036/037, found that `crossref.py` and `semantic_scholar.py` don't catch `JSONDecodeError` when parsing API responses. If an API returns malformed JSON (network issues, API bugs, rate limiting HTML), the CLI crashes with an unhandled exception.

## Affected Files

### `src/erdos/core/clients/crossref.py`

```python
# Before fix - NO ERROR HANDLING
return response.json()  # type: ignore[no-any-return]
```

### `src/erdos/core/clients/semantic_scholar.py`

```python
# Before fix - catches HTTPError but not JSONDecodeError
try:
    response = fetch_with_retry(url, ...)
    data = response.json()  # Could raise JSONDecodeError
except requests.HTTPError as e:
    # Only catches HTTP errors, not JSON errors
```

## Steps to Reproduce

1. Simulate malformed JSON response (network interception or mock)
2. Run `erdos refs s2 citations <doi>`
3. Observe unhandled `json.JSONDecodeError`

## Expected Behavior

Graceful error with structured `CLIOutput.err()` and helpful message.

## Actual Behavior

```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Root Cause

Missing try/except around `response.json()` calls. Other clients (exa.py) handle this correctly.

## Fix

Wrap `response.json()` calls in try/except:

```python
try:
    data = response.json()
except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
    snippet = response.text[:200].replace('\n', '\\n')
    logger.error(
        "Invalid JSON for %s (status %d): %s",
        url,
        response.status_code,
        snippet,
    )
    raise
```

## Implementation Notes

- Implemented JSON decode handling in:
  - `src/erdos/core/clients/crossref.py`
  - `src/erdos/core/clients/semantic_scholar.py`
- Ensured CLI returns structured errors (no traceback) for invalid JSON:
  - `src/erdos/commands/refs_s2.py`
- Added regression coverage:
  - `tests/unit/commands/test_refs_s2.py`

## Related

- Architecture audit: SPEC-036/037 prep
- Correct pattern in: `src/erdos/core/clients/exa.py:243-252`
