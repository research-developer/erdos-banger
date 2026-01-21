# Marker (PDF → Markdown) (Vendor Notes)

Marker converts PDFs into Markdown (and other formats) using local ML models and optional LLM backends. `erdos-banger` uses it as the primary converter for SPEC-019 (`erdos convert` and `erdos ingest --pdf`).

## Project / Docs

- Repo: https://github.com/datalab-to/marker
- Quickstart + settings: https://github.com/datalab-to/marker

## Runtime Settings (Environment Variables)

Marker documents that the torch device is auto-detected, but you can override it via `TORCH_DEVICE` (e.g., `cuda`, `cpu`). For Apple Silicon, `mps` is a valid torch device when supported by your PyTorch build.

Marker also documents memory-related knobs (e.g., `INFERENCE_RAM`) — consult the upstream settings section.

## Testing Guidance

- Unit tests should not depend on Marker being installed.
- Mock at the converter boundary and assert our CLI/output contract, not Marker internals.
