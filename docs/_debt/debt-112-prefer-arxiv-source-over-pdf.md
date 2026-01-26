# DEBT-112: Prefer arXiv Source Over PDF Conversion

**Created:** 2026-01-26
**Priority:** P3
**Status:** Fixed
**Fixed:** 2026-01-26
**Component:** `erdos ingest`, `erdos.core.ingest`

## Summary

When ingesting literature, the system should prefer arXiv LaTeX source over PDF conversion. The current workflow often falls back to PDF → marker conversion, which is slower, more error-prone, and requires a heavy ML dependency.

## Evidence

For Problem 848 (Sawhney paper, arXiv:2511.16072):

| Approach | Size | Quality | Dependencies |
|----------|------|---------|--------------|
| arXiv source tarball | 2.4MB | Clean LaTeX, perfect math | `tarfile` (stdlib) |
| PDF conversion | 360KB PDF → marker | OCR artifacts, math errors | marker-pdf (heavy ML) |

The LaTeX source is:
- Instantly available via `https://arxiv.org/e-print/{arxiv_id}`
- Already structured (sections, equations, references)
- No OCR/conversion needed
- Works without GPU/MPS

## Current State

1. ✅ `erdos refs add` now exists - arXiv papers can be added to problems
2. ✅ **BUG-040** fixed - marker-pdf v1 API integration works
3. ✅ `arxiv_download.py` implements tarball download + LaTeX extraction
4. ✅ Happy path (arXiv source) is now reachable

**Verified workflow:**
```bash
uv run erdos refs add 848 --arxiv 2511.16072  # ✅ Adds reference
uv run erdos ingest 848 --force               # ✅ Downloads tarball + extracts
ls literature/cache/arxiv/extracted/2511.16072/*.tex  # ✅ LaTeX available
```

## Remaining Work

The pipeline works, but could be improved:

1. **Documentation**: Skills/docs should explicitly recommend arXiv source path over PDF
2. **CLI hints**: `erdos ingest --help` should mention arXiv source preference
3. **Verification**: Add test coverage for the arXiv-preferred path

## Acceptance Criteria

- [x] `erdos refs add 848 --arxiv 2511.16072` works ✅
- [x] Ingest downloads tarball when arXiv ID present ✅
- [x] PDF fallback documented in `erdos ingest --help` ✅
- [x] Skills updated to recommend arXiv source path ✅

## Related

- BUG-039: Ingest Cannot Discover Papers
- BUG-040: Marker PDF Conversion Broken (fixed)
- `src/erdos/core/ingest/arxiv_download.py`: Existing tarball logic
