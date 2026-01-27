# Marker (PDF → Markdown) (Vendor Notes)

Marker converts PDFs into Markdown (and other formats) using local ML models and optional LLM backends. `erdos-banger` uses it as the primary converter for SPEC-019 (`erdos convert` and `erdos ingest --pdf`).

## Project / Docs

- Repo: <https://github.com/VikParuchuri/marker>
- PyPI: <https://pypi.org/project/marker-pdf/>

## ⚠️ API Drift (marker-pdf 1.x)

**BUG-040 (fixed in `b7ceb6f`)**: marker-pdf has shipped multiple incompatible
constructor/config surfaces across 1.x. Our wrapper in
`src/erdos/core/pdf/converter.py` uses feature detection and fallbacks so
`erdos convert` / `erdos ingest --pdf` keep working across versions.

Observed differences across 1.x releases:

- `ConfigParser(...)` may require a `cli_options` dict instead of a no-arg ctor.
- Some versions expose `ConfigParser.get_converter_cls()`; others require
  importing `marker.converters.pdf.PdfConverter` directly.
- `PdfConverter(...)` may or may not accept a `llm_service=` kwarg. Our wrapper
  retries without it when needed.

Examples (illustrative only; prefer the wrapper):

Older API (<1.0.0, not supported by this repo):

```python
from marker.config.parser import ConfigParser
config = ConfigParser()  # No args
```

Newer API (1.x):

```python
from marker.config.parser import ConfigParser
config = ConfigParser(cli_options={})  # Requires dict
```

Updated integration example (mirrors upstream):

```python
from marker.config.parser import ConfigParser
from marker.models import create_model_dict

cli_options = {"output_format": "markdown"}
config_parser = ConfigParser(cli_options=cli_options)

converter_cls = config_parser.get_converter_cls()
converter = converter_cls(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)
rendered = converter(str(pdf_path))
markdown = getattr(rendered, "markdown", str(rendered))
```

## Runtime Settings (Environment Variables)

Marker documents that the torch device is auto-detected, but you can override it via `TORCH_DEVICE` (e.g., `cuda`, `cpu`). For Apple Silicon, `mps` is a valid torch device when supported by your PyTorch build.

Marker also documents memory-related knobs (e.g., `INFERENCE_RAM`) — consult the upstream settings section.

## Testing Guidance

- Unit tests should not depend on Marker being installed.
- We stub `sys.modules` for the `marker.*` package tree and assert our wrapper calls into the v1 API surface (`tests/unit/pdf/test_converter.py`).
