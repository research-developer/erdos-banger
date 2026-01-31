# DEBT-125: Missing Test Edge Cases Across New Bug Fixes

**Priority:** P2
**Status:** Open
**Found:** 2026-01-31
**Component:** `tests/unit/`

## Summary

The bug fixes from commit 005dc83 have test coverage for happy paths but missing edge cases that could cause production issues.

## Missing Edge Cases

### test_exa.py

- No test for empty `results` array from API
- No test for malformed/truncated summaries
- No test for `Retry-After` header as integer (spec allows both string and int)

### test_converter.py

- No test for PDFs under 1KB (corrupted headers)
- Thread-safety test doesn't verify actual race conditions, only env var restoration
- No test for marker LLM service incompatibility

### test_arxiv_extract.py

- No test for symlinks in tarball (security: `../../../etc/passwd`)
- No test for tar bombs (deeply nested directories)
- No test for mixed-encoding files (UTF-8 + Latin-1)
- Empty content after LaTeX validation not tested

### test_fetch.py

- No test for URL redirects (HTTP 301/302)
- No test for 403 Forbidden responses
- No test for Content-Type mismatch (`text/html` with `.pdf` extension)
- No test for `data:` or `file:` URI schemes (security)

## Impact

- Edge cases could cause silent failures in production
- Security issues (symlinks, data URIs) untested
- Error handling paths not exercised

## Recommended Fix

Add targeted edge case tests for each area, prioritizing:
1. Security issues (symlinks, URI schemes)
2. Error handling (403, redirects, malformed data)
3. Boundary conditions (empty results, size limits)

## Related

- BUG-054: arXiv gzip fallback
- BUG-055: URL-only PDF references
- BUG-056: Exa search_type config
