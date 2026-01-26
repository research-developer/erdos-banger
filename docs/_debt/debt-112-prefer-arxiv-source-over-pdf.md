# DEBT-112: Prefer arXiv Source Over PDF Conversion

**Created:** 2026-01-26
**Priority:** P2
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

1. **BUG-039** blocks adding arXiv papers to problems (`erdos refs add` doesn't exist)
2. **BUG-040** fixed marker-pdf v1 API integration (PDF conversion is no longer blocked)
3. `arxiv_download.py` already implements tarball download + LaTeX extraction
4. But the happy path (arXiv source) is unreachable due to BUG-039

## Proposed Fix

After BUG-039 is fixed (adding `erdos refs add`), ensure:

1. **Default to source**: When arXiv ID is available, download tarball first
2. **PDF as fallback**: Only convert PDF if no arXiv source exists
3. **Document in workflow**: Skills and docs should recommend arXiv source path

## Workaround (Manual)

```bash
# Download source tarball (matches `src/erdos/core/literature_paths.py`)
mkdir -p literature/cache/arxiv/2511.16072
curl -sL "https://arxiv.org/e-print/2511.16072" -o literature/cache/arxiv/2511.16072/source.tar.gz

# Inspect contents (best-effort)
tar -tf literature/cache/arxiv/2511.16072/source.tar.gz | rg "\\.tex$" | head
```

## Acceptance Criteria

- [ ] BUG-039 fixed: `erdos refs add 848 --arxiv 2511.16072` works
- [ ] Ingest prefers tarball when arXiv ID present
- [ ] PDF fallback documented in `erdos ingest --help`
- [ ] Skills updated to recommend arXiv source path

## Related

- BUG-039: Ingest Cannot Discover Papers
- BUG-040: Marker PDF Conversion Broken (fixed)
- `src/erdos/core/ingest/arxiv_download.py`: Existing tarball logic
