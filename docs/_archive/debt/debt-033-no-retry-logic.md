# Technical Debt 033: No Retry Logic for Transient Network Failures

**Date:** 2026-01-21
**Status:** Fixed
**Fixed In:** 11a3519
**Priority:** P2 (Brittleness in batch operations)
**Impact:** Single transient failures cause entire operations to fail

## Summary

Network calls in the API clients and ingest module have no retry logic. A single timeout, DNS hiccup, or transient server error fails the entire operation, even when a retry would likely succeed.

## Evidence

### No Retry on Timeout

```python
# src/erdos/core/crossref_client.py:109 - Single attempt, no retry
response = requests.get(url, params=params, headers=headers, timeout=timeout)
response.raise_for_status()
```

### No Retry on Connection Error

```python
# src/erdos/core/arxiv_client.py:129 - Single attempt, no retry
response = requests.get(url, params=params, headers=headers, timeout=timeout)
response.raise_for_status()
```

### No Categorization of Errors

```python
# src/erdos/core/ingest/fetch.py:93 - Errors treated the same (generic message)
except (OSError, requests.RequestException) as e:
    error = f"Download failed: {e}"
```

The error message "Download failed" doesn't distinguish between:
- Timeout (temporary, should retry)
- 404 (permanent, won't retry)
- 429 (rate limited, should back off and retry)
- DNS failure (could retry)
- 500 (server error, could retry)

## Retry-Worthy Scenarios

| Error Type | Retry? | Strategy |
|------------|--------|----------|
| Timeout | Yes | Same delay, max 3 attempts |
| Connection error | Yes | Exponential backoff |
| 429 (rate limit) | Yes | Respect Retry-After header or back off |
| 5xx (server error) | Yes | Exponential backoff |
| 4xx (client error) | No | Permanent failure |
| DNS failure | Maybe | Single retry after delay |

## Acceptance Criteria

1. Add retry logic with exponential backoff for transient failures
2. Distinguish retry-worthy from permanent failures
3. Log retry attempts at DEBUG level
4. Cap total retries (e.g., max 3 attempts)
5. CI still passes (`make ci`)

## Recommended Implementation

If adding a dependency is acceptable, `tenacity` is a good fit:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
)
def fetch_crossref_work(doi: str, ...) -> dict[str, Any]:
    with requests.get(url, ...) as response:
        if response.status_code == 429:
            raise requests.exceptions.RetryError("Rate limited")
        response.raise_for_status()
        return response.json()
```

Or, avoid new dependencies with a simple manual implementation:

```python
def _fetch_with_retry(url: str, max_attempts: int = 3, **kwargs) -> requests.Response:
    last_error = None
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, **kwargs)
            if response.status_code == 429:
                delay = int(response.headers.get("Retry-After", 5))
                time.sleep(delay)
                continue
            return response
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            time.sleep(2 ** attempt)  # Exponential backoff
    raise last_error or requests.RequestException("Max retries exceeded")
```

## Related

- DEBT-031: Rate limiting is not centralized (constant unused)
- DEBT-032: HTTP responses not closed with context managers
