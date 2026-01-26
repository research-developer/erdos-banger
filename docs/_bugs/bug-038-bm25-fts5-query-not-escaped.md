# Bug: BM25 search doesn't escape FTS5 special characters

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** (pending)

## Description

The `BM25Search.search()` method passes user queries directly to FTS5 without escaping special characters. Queries containing hyphens, parentheses, or FTS5 operators (AND, OR, NOT) crash with `OperationalError`.

## Affected Files

### `src/erdos/core/search/bm25.py:73`

```python
# Current - NO ESCAPING
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

`BM25Search.search()` passes the raw query to FTS5 without escaping. The `ask/retrieval.py` has proper escaping (lines 45-63), but `bm25.py` doesn't use it.

**Correct pattern from `retrieval.py`:**
```python
# Extract alphanumeric tokens
tokens = re.findall(r"[a-z0-9]+", haystack)
# Quote each token
terms = [f'"{t}"' for t in unique if t]
# Join with OR
query = " OR ".join(terms[:MAX_QUERY_TERMS])
```

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

## Impact

- **Hybrid search:** Broken for any query with hyphens, parentheses, or FTS5 operators
- **Direct BM25 search:** Also affected (`erdos search "sum-free"`)
- **Semantic search:** NOT affected (doesn't use FTS5)
- **Ask command:** NOT affected (uses its own escaping in `retrieval.py`)

## Related

- `src/erdos/core/ask/retrieval.py:45-63` - Correct escaping pattern
- `docs/architecture/rag-system.md` - RAG documentation
