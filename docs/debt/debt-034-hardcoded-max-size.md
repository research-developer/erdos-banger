# Technical Debt 034: Hardcoded MAX_SIZE Instead of Using Constant

**Date:** 2026-01-21
**Status:** Open
**Priority:** P3 (Maintenance burden)
**Impact:** Duplicate magic numbers; if limit needs changing, multiple places must be updated

## Summary

The maximum TeX file size is defined in two places with the same value, violating DRY principle.

## Evidence

### Local Definition (src/erdos/core/arxiv_client.py:153)

```python
def extract_arxiv_text(tarball_bytes: bytes) -> bytes:
    MAX_SIZE = 2 * 1024 * 1024  # 2 MiB - hardcoded locally
    ...
```

### Constant Definition (src/erdos/core/constants.py:49)

```python
MAX_TEX_FILE_SIZE = 2 * 1024 * 1024  # Maximum LaTeX file size to process (2 MiB).
```

The constant exists but is not used in `arxiv_client.py`.

## Acceptance Criteria

1. Import `MAX_TEX_FILE_SIZE` from constants in `arxiv_client.py`
2. Remove local `MAX_SIZE` definition
3. CI still passes (`make ci`)

## Fix

```python
# Before (src/erdos/core/arxiv_client.py)
def extract_arxiv_text(tarball_bytes: bytes) -> bytes:
    MAX_SIZE = 2 * 1024 * 1024
    ...

# After (src/erdos/core/arxiv_client.py)
from erdos.core.constants import MAX_TEX_FILE_SIZE

def extract_arxiv_text(tarball_bytes: bytes) -> bytes:
    # Use MAX_TEX_FILE_SIZE instead of local MAX_SIZE
    ...
```

## Related

- DEBT-020: Magic Numbers and Naming (previously fixed, this is a remnant)
