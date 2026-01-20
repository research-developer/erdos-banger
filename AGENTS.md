# Repository Guidelines

## Project Structure

- `src/erdos/`: Python package (CLI + core logic).
  - `src/erdos/cli.py`: top-level Typer app entrypoint.
  - `src/erdos/commands/`: CLI command modules (e.g., `list_cmd.py`, `search.py`).
  - `src/erdos/core/`: core services (models, loader, search index, ingest, Lean runner).
- `tests/`: pytest suite (`unit/`, `integration/`, `e2e/`) and `tests/fixtures/`.
- `docs/`: specs, bug/debt decks, and process docs.
- `formal/lean/`: Lean 4 project scaffold used by Lean integration.
- `scripts/`: helper scripts (e.g., `scripts/smoke-test.sh`, LLM wrappers).
- `ralph.log`: intentionally tracked marker file for the Ralph Wiggum loop. It may be reset between runs; never log secrets.

## Build, Test, and Development Commands

Use `make` (preferred) or `uv` directly:

- `make sync`: install dependencies (uses `uv`).
- `make ci`: run formatting, lint, typecheck, and coverage gates (CI equivalent).
- `make test`: run tests skipping Lean + network (`-m "not requires_lean and not requires_network"`).
- `make smoke`: run CLI smoke test (`scripts/smoke-test.sh`).
- Example CLI run: `uv run erdos --help`

## Coding Style & Naming Conventions

- Python 3.11 (`.python-version`).
- Formatting/linting: Ruff (`make format`, `make lint`).
- Type checking: mypy strict (`make typecheck`).
- Prefer small, testable “core logic” helpers and thin Typer callbacks.
- Follow existing naming patterns (e.g., `list_()` for the reserved keyword).

## Testing Guidelines

- Framework: pytest; markers include `e2e`, `slow`, `requires_lean`, `requires_network`.
- Coverage target: `--cov-fail-under=80` (see `make cov`).
- New features should include unit tests and (when appropriate) integration tests using `tests/fixtures/`.

## Commits & Pull Requests

- Commit style: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`), often with scopes (e.g., `fix(core): ...`).
- Before opening a PR: run `make ci` and ensure `git status` is clean.
- PRs should include a short summary, test plan, and links to relevant specs/issues. CodeRabbit reviews are enabled on PRs.
