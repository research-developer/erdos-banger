# Marker (PDF → Markdown) (Vendor Notes)

Marker converts PDFs into Markdown (and other formats) using local ML models and optional LLM backends. `erdos-banger` uses it as the primary converter for SPEC-019 (`erdos convert` and `erdos ingest --pdf`).

## Project / Docs

- Repo: https://github.com/VikParuchuri/marker
- PyPI: https://pypi.org/project/marker-pdf/

## ⚠️ Breaking Change (marker-pdf >= 1.0.0)

**BUG-040 (fixed in `b7ceb6f`)**: marker-pdf 1.0.0+ changed both the `ConfigParser` and converter construction APIs. Our wrapper now matches Marker’s own `convert_single` entrypoint pattern.

Old API (pre-1.0):
```python
from marker.config.parser import ConfigParser
config = ConfigParser()  # No args
```

New API (1.0.0+):
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
