# Bug: zbMATH search methods don't handle 404 errors

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-25
**Fixed:** 2026-01-25
**Commit:** 05bc9ec

## Description

Several `ZbMathClient` methods in `src/erdos/core/clients/zbmath.py` don't handle HTTP 404 errors, causing them to propagate as uncaught exceptions instead of returning `None`/empty list like other not-found cases.

Affected methods:
- `_search_by_identifier()` - returns `None` on 404
- `search_by_msc()` - returns `[]` on 404
- `search_by_title()` - returns `[]` on 404

## Steps to Reproduce

```python
from erdos.core.clients.zbmath import ZbMathClient

client = ZbMathClient()
# This uses _search_by_identifier because it has "." in the ID
entry = client.get_by_zbl_id('9999.99999', use_cache=False)
```

Or via CLI:

```bash
uv run erdos refs zbmath --zbl 9999.99999
# Error: zbMATH API error: 404 Client Error: Not Found for url: ...

uv run erdos search --msc 99XX99
# Error: zbMATH API error: 404 Client Error: Not Found for url: ...
```

## Expected Behavior

Non-existent entries should return `None` (or "Entry not found" in CLI), consistent with:
- `get_by_zbl_id()` with numeric IDs (handles 404 at lines 410-414)
- `get_by_doi()` (handles 404 at lines 497-501)
- Other clients (S2, Exa, etc.)

## Actual Behavior

`requests.HTTPError` with 404 status propagates up the call stack, resulting in a traceback or cryptic error message.

## Root Cause

In `zbmath.py` line 445-446, the `_search_by_identifier()` method has:

```python
except requests.HTTPError:
    raise
```

This re-raises all HTTP errors without checking if it's a 404 (not found), unlike the direct lookup path in `get_by_zbl_id()` which handles 404s properly:

```python
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
        return None
    raise
```

## Fix

Add 404 handling to `_search_by_identifier()`:

```python
except requests.HTTPError as e:
    if e.response is not None and e.response.status_code == 404:
        self._cache_zbl_entry(cache_key, None, use_cache=use_cache)
        return None
    raise
```

## Related

- `get_by_zbl_id()` - calls `_search_by_identifier()` for identifier-format IDs
- `get_by_doi()` - has correct 404 handling pattern to follow
- Other clients handle 404s correctly (S2, OpenAlex, Crossref)
