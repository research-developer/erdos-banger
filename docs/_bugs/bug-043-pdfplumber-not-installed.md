# BUG-043: INVALIDATED - pdfplumber is Intentionally Optional

**Date:** 2026-01-26
**Severity:** N/A (False positive)
**Status:** Invalidated

## Summary

~~The `erdos convert` command claims to support `pdfplumber` as a fallback converter, but the module is not installed.~~

**WRONG.** This is intentional design:

1. `marker-pdf` is the primary converter (optional dependency: `uv sync --extra pdf`)
2. `pdfplumber` is graceful degradation - users can install manually if needed
3. The code correctly checks `is_pdfplumber_available()` before attempting to use it
4. Error message "Converter 'pdfplumber' not available, using 'marker'" is correct behavior

## Why This Is Not a Bug

From `pyproject.toml`:
```toml
[project.optional-dependencies]
pdf = [
    "marker-pdf>=1.0.0",  # GPL - see SPEC-019 for license rationale
]
```

- Marker is GPL licensed, so it's optional
- pdfplumber is MIT but low quality for math, so not bundled
- Users who need pdfplumber can: `uv add pdfplumber`

## Real Issue (Minor)

Could improve error messaging when neither converter is available to suggest:
```
No PDF converter available. Install with:
  - Marker (recommended): uv sync --extra pdf
  - pdfplumber (fallback): uv add pdfplumber
```

## Related

- BUG-040: Marker PDF conversion broken (real bug - marker is installed but API changed)
