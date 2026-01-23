# DEBT-079: Dead Code in `literature_paths.py` (SPEC-019 Stubs)

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Superseded by BUG-022

> **Note:** This was initially flagged as dead code, but investigation revealed it's part of an **incomplete feature** (SPEC-019 PDF integration for `erdos ingest`). The functions should be **wired in**, not removed. See BUG-022 for the actual fix.

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
- These functions were likely scaffolding that was never integrated

## Proposed Fix

**Option A (Recommended):** Delete the unused functions
- Remove `get_pdf_cache_path()`, `get_pdf_extract_path()`, `sanitize_reference_id()`
- These are 35 lines of dead code
- If needed later, they can be re-added with actual usage

**Option B:** Implement PDF caching
- Wire these functions into `erdos ingest` or `erdos convert`
- Add tests for the functions
- This is a feature enhancement, not a debt fix

## Acceptance Criteria

- [ ] Unused PDF path functions removed from `literature_paths.py`
- [ ] No import errors in codebase
- [ ] `make ci` passes

## Impact

- **Risk:** Very low (dead code removal)
- **Effort:** ~5 minutes
- **Benefit:** Cleaner codebase, reduced confusion about SPEC-019 implementation

## References

- `src/erdos/core/literature_paths.py:52-87`
- SPEC-019: `docs/_archive/specs/spec-019-pdf-conversion.md`
- Detection tool: [Vulture](https://github.com/jendrikseipp/vulture)
