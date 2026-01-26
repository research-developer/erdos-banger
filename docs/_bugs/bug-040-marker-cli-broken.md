# BUG-040: Marker PDF Conversion Broken

**Date:** 2026-01-26
**Severity:** P1 (High - blocks PDF workflow)
**Status:** Open
**Component:** `erdos convert`, `erdos.core.pdf.converter`

## Summary

The `erdos convert` command fails with a ConfigParser error. PDF conversion is completely non-functional.

## Reproduction

```bash
$ uv run erdos convert literature/papers/0848/sawhney_problem_848.pdf --output test.md
Converting sawhney_problem_848.pdf...
2026-01-26 13:19:39 [WARNING] erdos.core.pdf.converter: Marker conversion failed for literature/papers/0848/sawhney_problem_848.pdf: ConfigParser.__init__() missing 1 required positional argument: 'cli_options'
Error: Conversion error: ConfigParser.__init__() missing 1 required positional argument: 'cli_options'
```

## Root Cause

**CONFIRMED:** Breaking change in `marker-pdf` library API.

Old API (our code):
```python
config = ConfigParser()  # No args
```

New API (marker >= 1.0.0):
```python
config = ConfigParser(cli_options={})  # Requires dict
```

Verified with:
```bash
$ uv run python -c "from marker.config.parser import ConfigParser; import inspect; print(inspect.signature(ConfigParser.__init__))"
(self, cli_options: dict)
```

## Location

`src/erdos/core/pdf/converter.py:227`:
```python
config = ConfigParser()  # BUG: missing cli_options argument
```

## Impact

- Cannot convert PDFs to markdown/text
- Cannot ingest PDF papers into the literature pipeline
- The `--pdf` flag on `erdos ingest` is broken
- Research workflow is blocked for non-arXiv papers

## Fix

Change line 227 in `converter.py`:
```python
# Before (broken):
config = ConfigParser()

# After (fixed):
config = ConfigParser(cli_options={})
```

May also need to update how `use_llm`, `llm_service`, and `force_ocr` are set - check if these are still valid attributes or need to go in `cli_options` dict.

## Related

- BUG-043: INVALIDATED (pdfplumber is intentionally optional)
- marker-pdf docs: https://github.com/VikParuchuri/marker
