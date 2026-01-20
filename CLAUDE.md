# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

CLI toolkit for collaborative research on Erdős problems (1,135 curated math problems). Pipeline: problem data → literature ingestion → FTS5 search → RAG Q&A → Lean 4 formalization.

## Build & Development Commands

```bash
# Setup (requires uv: https://docs.astral.sh/uv/)
git submodule update --init --recursive
uv sync

# Run CLI
uv run erdos --version
uv run erdos list --status open --limit 5
uv run erdos show 6

# Full CI check (run before every commit)
make ci                    # format-check + lint + typecheck + cov

# Individual checks
make lint                  # ruff check
make format                # ruff format
make typecheck             # mypy src/ tests/
make test                  # pytest (skip Lean + network)
make test-all              # pytest (all tests)
make smoke                 # CLI smoke test
```

## Running Tests

```bash
# Fast tests (default, excludes Lean and network)
uv run pytest -m "not requires_lean and not requires_network"

# Single test file
uv run pytest tests/unit/test_models.py

# Single test function
uv run pytest tests/unit/test_models.py::test_specific_function -v

# With coverage
uv run pytest --cov=erdos --cov-fail-under=80 -m "not requires_lean and not requires_network"

# Run Lean-dependent tests (requires elan installed)
uv run pytest -m "requires_lean"
```

## Architecture

```
src/erdos/
├── cli.py              # Typer entry point, global flags (--json, --log-level)
├── commands/           # CLI subcommands (list, show, refs, search, lean, ingest, ask)
│   ├── presenter.py    # Shared output formatting (exit_with_result, CLIOutput)
│   └── *.py           # Each command module (list_cmd.py, show.py, etc.)
└── core/               # Business logic
    ├── models/         # Pydantic models (ProblemRecord, ReferenceRecord, CLIOutput, etc.)
    ├── ports.py        # Protocol “ports” for dependency inversion
    ├── context.py      # AppContext composition root (wiring concrete deps)
    ├── problem_loader.py  # Loads problems from YAML
    ├── search_index.py    # SQLite FTS5 search
    ├── lean_runner.py     # Lean 4 compilation wrapper
    ├── ingest.py          # Reference ingestion orchestration
    ├── ask.py             # RAG Q&A logic
    ├── crossref_client.py # Crossref API client
    └── arxiv_client.py    # arXiv API client
```

**Data flow:** Commands → Core functions → ProblemLoader/SearchIndex → Storage

**Key patterns:**
- Commands get dependencies via `erdos.commands.app_context.get_app_context()` (AppContext + Protocol ports)
- All commands support `--json` for machine-readable output via `CLIOutput`
- Exit codes defined in `core/exit_codes.py` (ExitCode enum)
- Tests use `tests/fixtures/sample_problems.yaml` as test data

## Data Locations

- `data/problems_enriched.yaml` - Local enriched problem dataset (titles, statements, references) (gitignored)
- `src/erdos/data/problems_enriched.yaml` - Built-in sample dataset shipped with the package
- `data/erdosproblems/` - Upstream submodule (metadata only, do not modify)
- `literature/manifests/` - Reference metadata per problem
- `literature/cache/` - arXiv source tarballs (gitignored)
- `index/` - SQLite FTS5 index (gitignored)
- `formal/lean/` - Lean 4 project

## Ralph Wiggum Logs

- `ralph.log` is intentionally tracked in git as a run journal for the Ralph Wiggum loop.
- Do not delete or rewrite history in `ralph.log`.
- Never include API keys or other secrets in `ralph.log` (or any tracked file).

## Test Markers

```python
@pytest.mark.requires_lean    # Needs elan/Lean installed
@pytest.mark.requires_network # Needs network access
@pytest.mark.slow            # Long-running tests
@pytest.mark.e2e             # End-to-end tests
```

## Code Style

- Python 3.11+, strict mypy typing
- ruff for linting/formatting (configured in pyproject.toml)
- 80% minimum test coverage enforced
- All CLI output through Rich console or `exit_with_result()`

## Technical Debt Status

Track active technical debt in `docs/debt/README.md`. Resolved decks are archived under `docs/_archive/debt/`.

## Key Specs

- `docs/specs/master-vision.md` - Full architecture and roadmap
- `docs/_archive/specs/spec-010-ingest-command.md` - Ingest command (arXiv + Crossref)
- `docs/_archive/specs/spec-011-ask-command.md` - Ask command (RAG + LLM)
