# Technical Debt 020: Magic Numbers and Naming Issues

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** 6d8981c
**Priority:** P3 (Minor; clean up when touching nearby code)
**Impact:** Readability, maintainability, cognitive load

## Summary

The codebase contains scattered magic numbers without named constants, negative boolean parameters that read poorly, and some inconsistent naming patterns.

## Magic Numbers

### Truncation Lengths

| Value | Usage | Location |
|-------|-------|----------|
| `[:200]` | Preview truncation | 5 locations |
| `[:500]` | Message truncation | `src/erdos/core/lean_runner.py:214` |
| `[:100]` | Text preview | `src/erdos/commands/ask.py:47` |
| `[:50]` | Title truncation | `src/erdos/commands/ingest.py:56` |

**Locations of `[:200]`:**
- `src/erdos/core/models.py:353-355` (TextChunk preview)
- `src/erdos/core/search_index.py:206-208` (notes preview)
- `src/erdos/core/ask.py:143,158` (fallback snippets)
- `src/erdos/commands/search.py:157-159` (basic search snippet)

**Problem:** If we decide previews should be 250 chars, we must find and update all occurrences.

### Exit Codes

Some places use `ExitCode.ERROR`, others use raw `3`:

```python
# Good - uses enum
code=ExitCode.ERROR,

# Bad - magic number
code=3,  # What does 3 mean?
```

**Locations of `code=3`:**
- `src/erdos/commands/lean.py:113` - NotFound (should be `ExitCode.NOT_FOUND`)
- `src/erdos/commands/lean.py:142` - NotFound
- `src/erdos/commands/refs.py:54` - NotFound (inside `get_refs()`)
- `src/erdos/commands/show.py:69` - NotFound (inside `get_problem()`)

**Other raw exit codes:**
- `src/erdos/commands/list_cmd.py:69` - UsageError uses `code=2` (should be `ExitCode.USAGE_ERROR`)
- `src/erdos/commands/search.py:143` - UsageError uses `code=2` (should be `ExitCode.USAGE_ERROR`)
- `src/erdos/commands/lean.py:259` - `typer.Exit(code=5)` (should use `ExitCode.LEAN_ERROR`)

### Timeouts and Limits

| Value | Meaning | Location |
|-------|---------|----------|
| `120` | Lean compile timeout | `src/erdos/core/lean_runner.py:162` |
| `600` | Lake update timeout | `src/erdos/core/lean_runner.py:150` |
| `30.0` | HTTP timeout default | `src/erdos/core/ingest.py:50`, `src/erdos/core/arxiv_client.py:100`, `src/erdos/core/crossref_client.py:86` |
| `3.0` | Rate limit delay | `src/erdos/core/ingest.py:51`, `src/erdos/commands/ingest.py:124` |
| `10` | Default search limit | `src/erdos/commands/search.py:200` |
| `5` | Default RAG limit | `src/erdos/core/ask.py:202`, `src/erdos/commands/ask.py:94` |
| `25` | Max query terms | `src/erdos/core/ask.py:121` |
| `2 * 1024 * 1024` | Max tex file size | `src/erdos/core/arxiv_client.py:145` |

## Negative Boolean Parameters

### Current State

```python
no_llm: bool        # if not no_llm: ... (double negative)
no_download: bool   # if not no_download: ...
no_network: bool    # if not no_network: ...
no_mathlib: bool    # if not no_mathlib: ...
```

### Problem

Double negatives are hard to read:
```python
if not no_download:  # "if not no download" = "if download"?
    download_arxiv_source()
```

### Better Names

```python
enable_llm: bool     # if enable_llm: ...
download: bool       # if download: ...
allow_network: bool  # if allow_network: ...
fetch_mathlib: bool  # if fetch_mathlib: ...
```

Or use positive flags with defaults:
```python
skip_llm: bool = False      # Positive name, False default
skip_download: bool = False
offline: bool = False       # Clear meaning
```

## Naming Inconsistencies

### Module Naming

```python
list_cmd.py  # Because 'list' is reserved
```

Could be: `listing.py`, `problems.py`, or `list_problems.py`

### Private Function Prefixes

Mixed conventions:
```python
_print_human()        # Private presenter
_get_stable_key()     # Private helper
_load_raw()           # Private loader method
_error_details()      # Private helper
```

This is fine. Tests currently *do not* import private helpers directly, but do sometimes reach into internals (e.g., `loader._cache`) when asserting lazy-loading behavior.

## Proposed Fix

### Phase 1: Define Constants Module

```python
# src/erdos/core/constants.py (to create)
"""Application-wide constants."""

# Preview/truncation lengths
PREVIEW_LENGTH = 200
MESSAGE_TRUNCATION = 500
TITLE_TRUNCATION = 50

# Timeouts (seconds)
DEFAULT_HTTP_TIMEOUT = 30.0
LEAN_COMPILE_TIMEOUT = 120
LAKE_UPDATE_TIMEOUT = 600

# Rate limiting
API_RATE_LIMIT_DELAY = 3.0

# Search defaults
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_RAG_LIMIT = 5
MAX_QUERY_TERMS = 25

# Size limits
MAX_TEX_FILE_SIZE = 2 * 1024 * 1024  # 2 MiB
```

### Phase 2: Replace Magic Numbers

```python
# Before
preview=problem.notes[:200]

# After
from erdos.core.constants import PREVIEW_LENGTH
preview=problem.notes[:PREVIEW_LENGTH]
```

### Phase 3: Fix Exit Code Magic Numbers

```python
# Before
code=3,

# After
code=ExitCode.NOT_FOUND,
```

### Phase 4: Rename Boolean Parameters

This is a **breaking change** for CLI users. Options:

**Option A: Add New Flags, Deprecate Old**
```python
@app.callback()
def ingest(
    # New positive flags
    download: bool = True,
    network: bool = True,
    # Deprecated negative flags (hidden)
    no_download: bool = typer.Option(False, hidden=True),
    no_network: bool = typer.Option(False, hidden=True),
):
    # Handle both for backward compatibility
    actual_download = download and not no_download
```

**Option B: Keep CLI Names, Fix Internal Names**
```python
@app.callback()
def ingest(
    no_download: bool = False,  # CLI stays same
):
    download = not no_download  # Internal positive name
    if download:
        ...
```

## Acceptance Criteria

- [ ] `constants.py` module created with all magic numbers
- [ ] All `[:200]` replaced with `PREVIEW_LENGTH`
- [ ] All `code=3` replaced with `ExitCode.NOT_FOUND`
- [ ] Internal boolean variables use positive names
- [ ] (Optional) CLI flags migrated to positive names with deprecation
- [ ] All tests pass

## Effort Estimate

Low - mostly mechanical find-and-replace with constants.

## References

- Robert C. Martin, "Clean Code" Chapter 17: Smells and Heuristics - "Magic Numbers"
- "Replace Magic Number with Symbolic Constant" refactoring
