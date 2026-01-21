# Technical Debt 032: HTTP Responses Not Closed with Context Managers

**Date:** 2026-01-21
**Status:** Open
**Priority:** P2 (Resource management)
**Impact:** Potential resource leaks in high-volume scenarios

## Summary

HTTP responses from `requests.get()` are not being closed explicitly or used with context managers. While Python's garbage collector will eventually clean these up, in high-volume batch operations this could lead to resource accumulation.

## Evidence

### src/erdos/core/crossref_client.py:109

```python
response = requests.get(url, params=params, headers=headers, timeout=timeout)
response.raise_for_status()
return response.json()  # Response not explicitly closed
```

### src/erdos/core/arxiv_client.py:129

```python
response = requests.get(url, params=params, headers=headers, timeout=timeout)
response.raise_for_status()
return response.text  # Response not explicitly closed
```

### src/erdos/core/ingest/fetch.py:70

```python
response = requests.get(source_url, timeout=timeout)
response.raise_for_status()
tarball_bytes = response.content  # Response not explicitly closed
```

## Best Practice

The `requests` library supports context manager protocol:

```python
with requests.get(url, ...) as response:
    response.raise_for_status()
    return response.json()
```

This ensures the underlying connection is released promptly.

## Impact Assessment

- **Low volume:** Minimal impact; GC handles cleanup
- **Batch ingestion:** Could accumulate connections during rapid API calls
- **Long-running processes:** Memory/connection growth over time

## Acceptance Criteria

1. Wrap all `requests.get()` calls in `with` statements
2. Verify no functional change to existing behavior
3. CI still passes (`make ci`)

## Recommended Implementation

```python
# Before
def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()

# After
def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    with requests.get(url, params=params, headers=headers, timeout=timeout) as response:
        response.raise_for_status()
        return response.json()
```

## Related

- DEBT-031: Rate limiting is not centralized (constant unused)
- DEBT-033: No retry logic for transient network failures
