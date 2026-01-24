# DEBT-079: Dead Code in `literature_paths.py` (SPEC-019 Stubs)

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Resolved (BUG-022 fixed)
**Resolved:** 2026-01-23
**Commit:** 1c8889e

> **Note:** This was initially flagged as dead code, but investigation revealed it's part of an
> **incomplete feature** (SPEC-019 PDF integration for `erdos ingest`).
> The functions should be **wired in**, not removed. See **BUG-022** for the actual fix.

## Problem

Three functions in `core/literature_paths.py` were added for SPEC-019 (PDF conversion) but are never used anywhere in the codebase:

| Function | Line | Description |
|----------|------|-------------|
| `get_pdf_cache_path()` | 52 | Returns path for cached PDF files |
| `get_pdf_extract_path()` | 64 | Returns path for extracted PDF text |
| `sanitize_reference_id()` | 76 | Sanitizes DOI/arXiv IDs for filesystem |

## Evidence

### 1. Vulture Detection

```bash
$ uv run vulture src/erdos/ --min-confidence 60
src/erdos/core/literature_paths.py:52: unused function 'get_pdf_cache_path' (60% confidence)
src/erdos/core/literature_paths.py:64: unused function 'get_pdf_extract_path' (60% confidence)
src/erdos/core/literature_paths.py:76: unused function 'sanitize_reference_id' (60% confidence)
```

### 2. Grep Verification

```bash
$ grep -r "get_pdf_cache_path\|get_pdf_extract_path\|sanitize_reference_id" src/
# Only matches are the definitions themselves
```

### 3. Test Coverage

`tests/unit/core/test_literature_paths.py` only tests:
- `get_manifest_path()`
- `get_arxiv_cache_path()`
- `get_arxiv_extract_path()`

The PDF functions have **no test coverage**.

### 4. SPEC-019 Context

SPEC-019 (PDF Conversion) is marked **Complete** (`docs/_archive/specs/spec-019-pdf-conversion.md`), but the implementation uses a different approach:
- `erdos convert` writes to stdout or user-specified path
- No automatic caching to `literature/cache/pdf/` is implemented
- These functions were scaffolding that was never integrated

## Proposed Fix

No direct fix here. This deck exists only as the audit trail for the false-positive “dead code”
classification.

**Correct action:** implement **BUG-022** (wire `erdos ingest --pdf` end-to-end). Once BUG-022 is
fixed, these functions become used and this deck can be archived.

## Acceptance Criteria

- [ ] BUG-022 is fixed (PDF caching/conversion uses these path helpers)
- [ ] `make ci` passes

## Impact

- **Risk:** None (documentation-only)
- **Effort:** None (implementation work tracked by BUG-022)
- **Benefit:** Prevents accidental deletion of SPEC-019 scaffolding

## References

- `src/erdos/core/literature_paths.py:52-87`
- SPEC-019: `docs/_archive/specs/spec-019-pdf-conversion.md`
- Detection tool: [Vulture](https://github.com/jendrikseipp/vulture)
