# Bug: arXiv single-file gzip extraction fails (not a tarball)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-30
**Fixed:** 2026-01-31
**Commit:** `005dc83`

## Description

The `extract_arxiv_text()` function in `src/erdos/core/clients/arxiv.py` assumes all arXiv source downloads are tar archives. However, some arXiv submissions are single `.tex` files compressed with gzip (not tar.gz). When this occurs, extraction fails with misleading "invalid header" errors.

## Affected Papers (Examples)

| arXiv ID | Paper | Actual Format |
|----------|-------|---------------|
| 2012.10409 | Illingworth "Chromatic profile of locally bipartite" | gzip-compressed single .tex file |
| 0905.2527 | Mubayi-Turán "Finding bipartite subgraphs efficiently" | gzip-compressed single .tex file |

## Steps to Reproduce

```bash
# Add reference and ingest
uv run erdos refs add 74 --arxiv 0905.2527
uv run erdos ingest 74

# Observe error:
# arXiv extraction failed for 0905.2527: file could not be opened successfully:
# - method gz: ReadError('invalid header')
# - method bz2: ReadError('not a bzip2 file')
# - method xz: ReadError('not an lzma file')
# - method tar: ReadError('invalid header')
```

## Evidence

The downloaded files ARE valid gzip files, but contain single `.tex` files, not tar archives:

```bash
$ file literature/cache/arxiv/0905.2527/source.tar.gz
gzip compressed data, was "bipalg.tex", last modified: Fri May 15 18:41:23 2009

$ file literature/cache/arxiv/2012.10409/source.tar.gz
gzip compressed data, was "Chrom_prof_loc_bip_accepted.tex", last modified: Mon Aug 21 16:14:57 2023
```

The `file` command shows these are gzip files containing `.tex` files directly (not tarballs).

## Expected Behavior

The extraction should:
1. First attempt to open as tar archive (current behavior)
2. If that fails, check if it's a plain gzip file containing a `.tex` file
3. If so, decompress with `gzip.decompress()` and return the content
4. Log appropriately at each fallback

## Actual Behavior

Extraction fails with unhelpful error message claiming all compression methods failed, when in reality the file is valid gzip but not a tarball.

## Root Cause

The `extract_arxiv_text()` function (line 176 of `arxiv.py`) uses `tarfile.open(fileobj=tar_buffer, mode="r:*")` which tries:
- gzip-compressed tar
- bzip2-compressed tar
- xz-compressed tar
- uncompressed tar

It does NOT handle the case where the download is just a gzip-compressed single file.

## Location

- **File:** `src/erdos/core/clients/arxiv.py`
- **Function:** `extract_arxiv_text()` (lines 147-194)

## Proposed Fix

```python
def extract_arxiv_text(tarball_bytes: bytes) -> bytes:
    """Extract text from arXiv source (tarball or single gzip file)."""
    tar_buffer = io.BytesIO(tarball_bytes)

    # First, try as tar archive
    try:
        with tarfile.open(fileobj=tar_buffer, mode="r:*") as tar:
            # ... existing tar extraction logic ...
    except tarfile.TarError:
        # Fallback: try as plain gzip-compressed single file
        tar_buffer.seek(0)
        try:
            import gzip
            decompressed = gzip.decompress(tarball_bytes)
            # Check if it looks like a .tex file
            if b"\\documentclass" in decompressed or b"\\begin{" in decompressed:
                logger.debug("Extracted as single gzip-compressed .tex file")
                return decompressed[:MAX_TEX_FILE_SIZE]
        except gzip.BadGzipFile:
            pass
        # If we get here, it's truly malformed
        raise ValueError("Could not extract arXiv source: neither tar nor gzip")
```

## Workaround

Manually decompress the cached file:

```bash
cd literature/cache/arxiv/0905.2527
gunzip -c source.tar.gz > ../../../extracts/arxiv/0905.2527/fulltext.txt
```

## Impact

- Papers in this format cannot be ingested automatically
- Affects an unknown percentage of arXiv submissions (likely single-author papers with simple submissions)
- Problem 74 specifically affected: 2 of 3 newly added arXiv papers failed

## Resolution

Implemented the proposed fix. The `extract_arxiv_text()` function now:
1. First attempts to open as tar archive (existing behavior)
2. On `tarfile.TarError`, falls back to `gzip.decompress()`
3. Validates content contains LaTeX markers (`\documentclass` or `\begin{`)
4. Returns decompressed content capped at `MAX_TEX_FILE_SIZE`

**Changes:**
- `src/erdos/core/clients/arxiv.py`: Added gzip fallback with LaTeX validation
- `tests/unit/clients/test_arxiv_extract.py`: Added 3 tests for gzip handling

## Related

- `erdos ingest` command
- Literature ingestion pipeline
- SPEC-010 (Ingest command specification)
