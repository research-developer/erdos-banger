# BUG-040: Marker PDF Conversion Broken (marker-pdf >= 1.0.0 API changes)

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** b7ceb6f
**Component:** `erdos convert`, `erdos.core.pdf.converter`

## Description

`erdos convert` (and `erdos ingest --pdf`) crashed with marker-pdf 1.0.0+ due to breaking API changes in Marker’s configuration and converter construction.

## Root Cause

Our wrapper used the pre-1.0 API:

- `ConfigParser()` without CLI options
- `PdfConverter(config=...)` construction
- Setting config flags as attributes on the ConfigParser instance

Marker 1.0.0+ expects CLI-style options passed into `ConfigParser` and a converter constructed from `config_parser.get_converter_cls()` with an explicit `artifact_dict` (from `create_model_dict()`).

## Fix

- Build a `cli_options` dict (`output_format="markdown"`, optionally `use_llm`, `llm_service`, `force_ocr`)
- Instantiate Marker config via `ConfigParser(cli_options=...)`
- Construct the converter via `config_parser.get_converter_cls()` and pass:
  - `artifact_dict=create_model_dict()`
  - `config=config_parser.generate_config_dict()`
  - `processor_list=config_parser.get_processors()`
  - `renderer=config_parser.get_renderer()`
  - `llm_service=config_parser.get_llm_service()`
- Extract Markdown from `rendered.markdown` with a `str(rendered)` fallback
- Include basic metadata in the conversion result (`use_llm`, `llm_service`, `force_ocr`, `page_count`)

## Tests

Added a regression test that does not require Marker to be installed:

- `tests/unit/pdf/test_converter.py::TestMarkerConversion::test_convert_with_marker_uses_marker_config_parser`

It stubs a minimal `marker.*` module tree via `sys.modules` and asserts our wrapper calls the new v1 API surface correctly.
