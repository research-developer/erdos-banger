# BUG-058: arXiv Gzip Extraction Vulnerable to Decompression Bombs

**Priority:** P3
**Status:** Open
**Found:** 2026-01-31
**Component:** `src/erdos/core/clients/arxiv.py`

## Summary

The gzip fallback in `extract_arxiv_text()` decompresses the entire file into memory before validating content, making it vulnerable to decompression bombs (zip bombs).

## Evidence

In `src/erdos/core/clients/arxiv.py` lines 200-210:

```python
try:
    decompressed = gzip.decompress(tarball_bytes)  # FULL decompression first
    if b"\\documentclass" in decompressed or b"\\begin{" in decompressed:
        return decompressed[:MAX_TEX_FILE_SIZE]  # Cap AFTER decompression
```

## Attack Scenario

1. A malicious or corrupted arXiv source could be a 1 MB gzip file
2. `gzip.decompress()` expands it to 10 GB in memory
3. Server/process crashes with OOM before the size cap is applied

## Expected Behavior

Decompression should be size-limited during extraction, not after.

## Actual Behavior

Full decompression happens before any size check, allowing memory exhaustion.

## Recommended Fix

Use streaming decompression with size limit:

```python
import gzip
from io import BytesIO

MAX_DECOMPRESS_SIZE = 10 * 1024 * 1024  # 10 MB safety limit

try:
    with gzip.GzipFile(fileobj=BytesIO(tarball_bytes)) as gz:
        decompressed = gz.read(MAX_DECOMPRESS_SIZE + 1)
        if len(decompressed) > MAX_DECOMPRESS_SIZE:
            raise ValueError("Decompressed content exceeds safety limit")
    # ... rest of validation
```

## Impact

- Low: arXiv sources are generally trusted
- Defensive measure, not actively exploited
- Could cause OOM in edge cases with corrupted files

## Related

- BUG-054: arXiv single-file gzip extraction (the fix that introduced this)
