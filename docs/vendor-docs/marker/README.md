# Marker (PDF → Markdown) (Vendor Notes)

Marker converts PDFs into Markdown (and other formats) using local ML models and optional LLM backends. `erdos-banger` uses it as the primary converter for SPEC-019 (`erdos convert` and `erdos ingest --pdf`).

## Project / Docs

- Repo: https://github.com/VikParuchuri/marker
- PyPI: https://pypi.org/project/marker-pdf/

## ⚠️ Breaking Change (marker-pdf >= 1.0.0)

**BUG-040:** The `ConfigParser` API changed in marker 1.0.0+.

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

Our code at `src/erdos/core/pdf/converter.py:227` needs updating.

## Runtime Settings (Environment Variables)

Marker documents that the torch device is auto-detected, but you can override it via `TORCH_DEVICE` (e.g., `cuda`, `cpu`). For Apple Silicon, `mps` is a valid torch device when supported by your PyTorch build.

Marker also documents memory-related knobs (e.g., `INFERENCE_RAM`) — consult the upstream settings section.

## Testing Guidance

- Unit tests should not depend on Marker being installed.
- Mock at the converter boundary and assert our CLI/output contract, not Marker internals.
