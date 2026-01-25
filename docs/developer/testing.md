# Testing

`erdos-banger` uses `pytest`, Ruff, and strict `mypy`. The canonical commands are in the Makefile.

## Common Commands

```bash
make format     # ruff format
make lint       # ruff check
make typecheck  # mypy src/ tests/
make test       # pytest (skips Lean + network)
make test-all   # pytest (includes markers)
make ci         # CI equivalent (format-check + lint + typecheck + coverage + audit)
```

## Markers

- `requires_network`: needs network access and API keys
- `requires_lean`: needs Lean tooling available (CI runs this in a container)
- `slow`, `e2e`: longer-running suites

## Local API Keys

Network tests read keys from your environment. For local convenience, `.env` is loaded automatically by `pytest-dotenv`.

```bash
# .env (gitignored)
EXA_API_KEY=...
SEMANTIC_SCHOLAR_API_KEY=...
OPENALEX_API_KEY=...
ARISTOTLE_API_KEY=...
```

## CLI Help Output & ANSI Codes

Typer/Rich can emit ANSI codes in help output. When asserting on `--help`, use the `strip_ansi` fixture (see `tests/conftest.py`).
