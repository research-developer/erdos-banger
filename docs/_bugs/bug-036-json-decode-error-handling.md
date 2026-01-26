# Bug: Crossref/Semantic Scholar clients missing JSONDecodeError handling

**Priority:** P1
**Status:** Open
**Found:** 2026-01-26
**GitHub Issue:** [#35](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/issues/35)

## Description

During architectural audit for SPEC-036/037, found that `crossref.py` and `semantic_scholar.py` don't catch `JSONDecodeError` when parsing API responses. If an API returns malformed JSON (network issues, API bugs, rate limiting HTML), the CLI crashes with an unhandled exception.

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

## Related

- Architecture audit: SPEC-036/037 prep
- Correct pattern in: `src/erdos/core/clients/exa.py:243-252`
