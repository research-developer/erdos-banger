# DEBT-122: Ingest Fetch Module Size Exceeds Threshold

**Priority:** P3
**Status:** Open
**Found:** 2026-01-31
**Component:** `src/erdos/core/ingest/fetch.py`

## Summary

The `fetch.py` module grew to 568 LOC (threshold: 500) after adding BUG-055 URL-only PDF reference handling. The additional complexity is justified for feature completeness.

## Evidence

```bash
$ wc -l src/erdos/core/ingest/fetch.py
     568 src/erdos/core/ingest/fetch.py
```

BUG-055 added:
- `_is_url_only_pdf_ref()` helper function
- `_process_url_only_pdf_reference()` function (~40 LOC)
- Updates to `_error_manifest_entry()` for synthetic IDs
- Branch logic in `process_all_references()`

## Justification

The module orchestrates reference processing which has inherent complexity:
1. Multiple entry points (`fetch_reference_entry`, `process_single_reference`, `process_all_references`)
2. Error handling with result objects
3. PDF, arXiv, and URL-only processing paths
4. Rate limiting and delay coordination

Splitting into submodules would increase import complexity without meaningful separation of concerns.

## Recommended Fix

Future refactoring options (when/if the module grows further):
1. Extract PDF processing to `fetch_pdf.py`
2. Extract arXiv processing to `fetch_arxiv.py`
3. Keep `fetch.py` as thin orchestration layer

## Impact

- Low: Module is well-tested and stable
- 68 LOC over threshold (13.6% overage)
- All new code has test coverage

## Related

- BUG-055: URL-only PDF reference handling (the fix that caused this overage)
- SPEC-019: PDF ingestion
- Commit `005dc83`: Main implementation commit
