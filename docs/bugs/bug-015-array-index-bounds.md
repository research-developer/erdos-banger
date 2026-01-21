# Bug: Array index access without bounds checking in API parsers

**Priority:** P2
**Status:** Open
**Found:** 2026-01-21
**Fixed:** (pending)
**Commit:** (pending)

## Description

Several places in the API response parsers access array indices without properly validating that the array has enough elements. This can cause `IndexError` or `TypeError` crashes when external APIs return unexpected data structures.

## Affected Locations

### 1. `src/erdos/core/crossref_client.py:42`

```python
if not title_list or not isinstance(title_list, list) or not title_list[0]:
    ...
title = title_list[0]  # Could IndexError on empty list with falsy first element
```

**Problem:** The condition `not title_list[0]` is evaluated AFTER checking `not title_list`, but an empty list `[]` is falsy, so it passes the first check. However, `[]` will fail at `title_list[0]` access.

**Fix:** Add explicit length check: `len(title_list) == 0`

### 2. `src/erdos/core/crossref_client.py:65`

```python
year_parts = date_parts[0]  # No check if date_parts has elements
```

**Problem:** `date_parts` could be an empty list, causing `IndexError`.

**Fix:** Add bounds check: `if date_parts and len(date_parts) > 0:`

### 3. `src/erdos/core/crossref_client.py:73`

```python
if container_title and isinstance(container_title, list) and container_title:
    venue = container_title[0]
```

**Problem:** The condition `container_title` is checked twice (redundant) but empty list `[]` still passes.

**Fix:** Change to: `if isinstance(container_title, list) and len(container_title) > 0:`

### 4. `src/erdos/core/search_index.py:345-346`

```python
problems = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
```

**Problem:** `fetchone()` can return `None` if no rows match. Accessing `[0]` on `None` raises `TypeError`.

**Fix:** Use pattern from lines 320 & 327: `row[0] if row else 0`

## Steps to Reproduce

1. Mock Crossref API to return `{"message": {"title": []}}` (empty title array)
2. Call `parse_crossref_work()`
3. Observe `IndexError: list index out of range`

## Expected Behavior

Parsers should handle malformed API responses gracefully, either:
- Raising a clear `ValueError` with context, OR
- Returning a default value with logging

## Actual Behavior

Crashes with `IndexError` or `TypeError` that don't indicate the root cause (malformed external data).

## Root Cause

Truthy checks (`if x:`) were used instead of explicit length checks (`if len(x) > 0:`). Python lists are falsy when empty, but the code structure assumes non-empty after the truthy check.

## Fix

Replace truthy checks with explicit length validation:

```python
# Before
if not title_list or not isinstance(title_list, list) or not title_list[0]:
    raise ValueError(...)
title = title_list[0]

# After
if not isinstance(title_list, list) or len(title_list) == 0:
    raise ValueError("Missing title in Crossref response")
title = title_list[0]
if not title:  # Validate content after safe access
    raise ValueError("Empty title in Crossref response")
```

## Related

- External API robustness
- Input validation patterns
