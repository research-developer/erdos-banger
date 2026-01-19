# Spec 018: DevX Makefile (Local Workflow Shortcuts)

> Adds a repo-root `Makefile` that provides stable, discoverable shortcuts for common development commands (uv/ruff/mypy/pytest/pre-commit).

**Status:** Complete
**Target:** v1.1
**Prerequisites (SSOT):**
- Tooling: `docs/_archive/specs/spec-001-dev-environment-tooling.md`
- Local hooks: `.pre-commit-config.yaml`
- Locked deps: `uv.lock`

---

## 0) Motivation

This project already standardizes on:

- `uv` for environments and dependency management
- `ruff` for lint + format
- `mypy` for strict typing
- `pytest` for tests
- `pre-commit` for consistent local enforcement

The missing DevX piece is a single, memorable entrypoint for common workflows (and for AI agents) that stays aligned with the real commands.

This spec is also consistent with the master vision’s mention of a Makefile/Justfile for harness workflows (`docs/specs/master-vision.md:683`).

---

## 1) Scope

### In scope

1. Add a repo-root `Makefile`.
2. Targets are thin wrappers around the existing SSOT commands (no new behavior).
3. Provide `make hooks` to install pre-commit hooks locally.

### Out of scope

- Making `make` the CI SSOT (CI remains defined by GitHub Actions workflows; workflows may invoke `make` targets as thin wrappers).
- Adding new runtime dependencies.
- Supporting Windows environments without GNU Make.

---

## 2) Implementation

Create:

- `Makefile` (repo root)

### Required targets (SSOT)

All targets must call `uv` (not `pip`).

- `help`: list available targets
- `sync`: `uv sync`
- `sync-frozen`: `uv sync --frozen`
- `lock`: `uv lock`
- `lock-check`: `uv lock --check`
- `format`: `uv run ruff format .`
- `format-check`: `uv run ruff format . --check`
- `lint`: `uv run ruff check .`
- `lint-fix`: `uv run ruff check . --fix`
- `typecheck`: `uv run mypy src/ tests/`
- `test`: `uv run pytest -m "not requires_lean and not requires_network"`
- `test-all`: `uv run pytest`
- `cov`: `uv run pytest --cov=erdos --cov-fail-under=80 -m "not requires_lean and not requires_network"`
- `pre-commit`: `uv run pre-commit run --all-files`
- `hooks`: `uv run pre-commit install --install-hooks`
- `smoke`: `./scripts/smoke-test.sh`
- `ci`: run `format-check`, `lint`, `typecheck`, `cov`

---

## 3) Acceptance Criteria

These commands must work from repo root:

```bash
make help
make sync-frozen
make format-check
make lint
make typecheck
make test
make pre-commit
make smoke
```
