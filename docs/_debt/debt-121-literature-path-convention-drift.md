# DEBT-121: Literature Path Convention Drift

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-30
**Fixed:** 2026-01-30
**Component:** `literature/` directory structure

## Summary

The actual file structure in `literature/` doesn't match the documented convention in `src/erdos/core/literature_paths.py` (SPEC-019).

## Documented Convention (literature_paths.py)

```python
# PDF cache: literature/cache/pdf/{reference_id}/paper.pdf
# PDF extracts: literature/extracts/pdf/{reference_id}/fulltext.md
# reference_id = sanitized DOI or arXiv ID (e.g., "10.1000_example")
```

## Actual State

```
# Three different PDF locations exist:
literature/papers/0074/                    # Manual downloads (legacy?)
literature/cache/pdf/0074/                 # Manual downloads (using problem_id)
literature/cache/arxiv/{arxiv_id}/         # CLI ingest (correct)

# Extracts use problem_id instead of reference_id:
literature/extracts/pdf/0074/*.md          # Using problem_id
literature/extracts/arxiv/{arxiv_id}/      # Using arxiv_id (correct)
```

## Specific Files Out of Spec

| File | Current Location | Spec Location |
|------|-----------------|---------------|
| erdos-hajnal-1968-infinite.pdf | `papers/0074/` | Should be `cache/pdf/{doi_or_key}/paper.pdf` |
| erdos-hajnal-1985-chromatic.pdf | `papers/0074/` | Should be `cache/pdf/{doi_or_key}/paper.pdf` |
| erdos-hajnal-szemeredi-1982-almost-bipartite.pdf | `papers/0074/` | Should be `cache/pdf/{doi_or_key}/paper.pdf` |
| rodl-1982-nearly-bipartite.pdf | `papers/0074/` | Should be `cache/pdf/{doi_or_key}/paper.pdf` |
| erdos-gyori-1991.pdf | `cache/pdf/0074/` | Should be `cache/pdf/{key}/paper.pdf` |

## Root Cause

1. Manual PDF downloads bypassed CLI conventions
2. `erdos convert` outputs to arbitrary paths (doesn't enforce spec)
3. No validation that files match `literature_paths.py` conventions
4. `literature/papers/` isn't even mentioned in the spec

## Impact

- Confusion about where files should go
- CLI may not find manually-placed PDFs
- Inconsistent paths make automation harder
- Hard to know if a file came from CLI or manual process

## Questions to Resolve

1. Should `literature/papers/` exist at all, or should everything be in `cache/`?
2. Should extracts be organized by `{problem_id}` or `{reference_id}`?
3. Should `erdos convert` enforce output path conventions?

## Proposed Fix

**Option A: Enforce Spec**
1. Move all PDFs from `papers/` to `cache/pdf/{reference_id}/`
2. Rename extracts to use `{reference_id}` not `{problem_id}`
3. Delete `literature/papers/` directory
4. Update `erdos convert` to auto-place output per spec

**Option B: Update Spec**
1. Document `literature/papers/{problem_id}/` as valid location for manual downloads
2. Allow `{problem_id}` as alternative to `{reference_id}` in paths
3. Keep both conventions but document when to use each

**Recommendation:** Option A (enforce spec) for consistency, but needs migration script.

## Related

- SPEC-019: PDF conversion conventions
- BUG-055: URL-only references not ingested
- `src/erdos/core/literature_paths.py`: Path convention module
