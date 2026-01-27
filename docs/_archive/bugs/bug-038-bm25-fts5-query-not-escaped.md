# Bug: BM25 search doesn't escape FTS5 special characters

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** 8c55500

## Description

The `BM25Search.search()` method passes user queries directly to FTS5 without escaping special characters. Queries containing hyphens, parentheses, or FTS5 operators (AND, OR, NOT) crash with `OperationalError`.

## Affected Files

### `src/erdos/core/search/bm25.py`

```python
# Before fix - NO ESCAPING
params: list[str | int] = [query]  # Raw query passed to FTS5
```

## Steps to Reproduce

```bash
# This works (no special characters)
uv run erdos search "prime numbers" --hybrid

# This crashes (hyphen interpreted as NOT operator)
uv run erdos search "sum-free sets" --hybrid
```

**Error:**
```
OperationalError: no such column: free
```

FTS5 interprets `sum-free` as `sum NOT free`, treating "free" as a column name.

## Expected Behavior

Query should be escaped or tokenized to handle special characters gracefully.

## Actual Behavior

```
OperationalError: no such column: free
```

## Root Cause

`BM25Search.search()` passed raw user input to FTS5 without normalization. At the time of discovery, `erdos ask` already normalized free-text queries; BM25 search did not.

## Fix

Option 1: Extract the escaping logic from `retrieval.py` into a shared utility and use it in `bm25.py`.

Option 2: Add a `safe_fts5_query()` function in `bm25.py`:

```python
import re

def safe_fts5_query(query: str) -> str:
    """Escape a query for safe FTS5 matching."""
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    if not tokens:
        return '""'  # Empty match
    quoted = [f'"{t}"' for t in tokens]
    return " OR ".join(quoted)
```

Then in `search()`:
```python
safe_query = safe_fts5_query(query)
params: list[str | int] = [safe_query]
```

## Implementation Notes

- Implemented `safe_fts5_query(...)` and applied it in `BM25Search.search()`.
- Reused the same escaping utility for `erdos ask` retrieval (programmatic queries use `allow_advanced_syntax=False`).
- Added regression coverage:
  - `tests/integration/test_search_index.py`

## Impact

- **Hybrid search:** Broken for any query with hyphens, parentheses, or FTS5 operators
- **Direct BM25 search:** Also affected (`erdos search "sum-free"`)
- **Semantic search:** NOT affected (doesn't use FTS5)
- **Ask command:** Not affected (uses safe query normalization)

## Related

- `docs/architecture/rag-system.md` - RAG documentation
