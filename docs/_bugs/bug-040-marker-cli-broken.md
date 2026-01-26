# BUG-040: Marker PDF Conversion Broken (TWO API Changes)

**Date:** 2026-01-26
**Severity:** P1 (High - blocks PDF workflow)
**Status:** Partially Fixed (1 of 2 changes done)
**Component:** `erdos convert`, `erdos.core.pdf.converter`

## Summary

The `erdos convert` command fails due to **TWO breaking API changes** in marker-pdf >= 1.0.0.

## Current State

| Change | Status | Location |
|--------|--------|----------|
| `ConfigParser()` → `ConfigParser(cli_options={})` | ✅ Fixed in working tree | Line 227 |
| `PdfConverter(config=...)` → `PdfConverter(artifact_dict=..., ...)` | ❌ NOT FIXED | Line 245 |

## Reproduction (After Partial Fix)

```bash
$ uv run erdos convert literature/papers/0848/sawhney_problem_848.pdf --output test.md
Converting sawhney_problem_848.pdf...
2026-01-26 13:37:07 [WARNING] erdos.core.pdf.converter: Marker conversion failed: PdfConverter.__init__() missing 1 required positional argument: 'artifact_dict'
Error: Conversion error: PdfConverter.__init__() missing 1 required positional argument: 'artifact_dict'
```

## Workaround

**The `marker_single` CLI WORKS:**
```bash
uv run marker_single literature/papers/0848/sawhney_problem_848.pdf --output_dir /tmp/output
```

This produces valid markdown. Our Python wrapper is what's broken.

## Root Cause

marker-pdf >= 1.0.0 changed both `ConfigParser` and `PdfConverter` APIs.

### API Change 1: ConfigParser (FIXED)

```python
# Old (broken):
config = ConfigParser()

# New (fixed in working tree):
config = ConfigParser(cli_options={})
```

### API Change 2: PdfConverter (NOT FIXED)

Old API:
```python
converter = PdfConverter(config=config)
```

New API:
```python
from marker.models import create_model_dict

converter = PdfConverter(
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),  # optional
    renderer=config_parser.get_renderer(),          # optional
    llm_service=config_parser.get_llm_service(),    # optional
    config=config_parser.generate_config_dict(),    # optional
)
```

Verified signatures:
```bash
$ uv run python -c "from marker.converters.pdf import PdfConverter; import inspect; print(inspect.signature(PdfConverter.__init__))"
(self, artifact_dict: Dict[str, Any], processor_list: Optional[List[str]] = None, renderer: str | None = None, llm_service: str | None = None, config=None)
```

## Location

`src/erdos/core/pdf/converter.py`:
- Line 227: `ConfigParser(cli_options={})` ✅ FIXED
- Line 245: `PdfConverter(config=config)` ❌ NEEDS FIX

## Fix Required

Update `convert_with_marker()` function in `src/erdos/core/pdf/converter.py`:

```python
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict  # ADD THIS IMPORT

# Configure Marker
config_parser = ConfigParser(cli_options={})

# Set options via cli_options dict if needed for LLM/OCR
# (check if use_llm, llm_service, force_ocr are still attributes or need cli_options)

# Create converter with new API
converter = PdfConverter(
    artifact_dict=create_model_dict(),
    config=config_parser.generate_config_dict(),
)

result = converter(str(pdf_path))
markdown = result.markdown if hasattr(result, "markdown") else str(result)
```

## Alternative Fix: Shell Out to CLI

Simpler approach - just call `marker_single` via subprocess:

```python
import subprocess

def convert_with_marker_cli(pdf_path: Path, output_dir: Path) -> str:
    result = subprocess.run(
        ["marker_single", str(pdf_path), "--output_dir", str(output_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConversionError(result.stderr)
    # Read the generated .md file from output_dir
    ...
```

## Impact

- Cannot convert PDFs to markdown/text via `erdos convert`
- Cannot ingest PDF papers into the literature pipeline
- Research workflow blocked for non-arXiv papers
- **Workaround exists:** Use `marker_single` CLI directly

## Related

- marker-pdf docs: https://github.com/VikParuchuri/marker
- PyPI: https://pypi.org/project/marker-pdf/
