"""Core domain and application services for erdos-banger.

This package contains the "business logic" used by CLI adapters in
`src/erdos/commands/`. Code is organized into bounded-context subpackages
(`ask/`, `ingest/`, `search/`, `loop/`, `research/`, etc.) with a small number of
stable top-level modules:

- `config.py` / `context.py`: centralized configuration and composition root
- `ports.py`: Protocol ports for dependency inversion
- `exit_codes.py`: CLI exit code conventions

Prefer importing from a bounded-context package (e.g., `erdos.core.search`) or
from curated export surfaces like `erdos.core.models`, rather than importing
from the package root.
"""
