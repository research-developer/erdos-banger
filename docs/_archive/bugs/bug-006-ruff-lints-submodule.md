# Bug: Ruff lints upstream submodule files (CI failure)

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-18
**Fixed:** 2026-01-18
**Commit:** 2f4124b

## Description

After adding the `teorth/erdosproblems` git submodule at `data/erdosproblems/`, the repo-wide lint step (`ruff check .`) starts linting the submodule's Python scripts and fails CI.

## Steps to Reproduce

```bash
uv run --frozen ruff check .
```

## Expected Behavior

Ruff should lint only this repository’s code (e.g., `src/` and `tests/`) and ignore third-party submodules.

## Actual Behavior

`ruff check .` reports lint violations inside `data/erdosproblems/scripts/*.py`.

## Root Cause

Ruff traverses the working tree when invoked on `.` and does not automatically exclude git submodules. The project does not currently configure `exclude`/`extend-exclude` for `data/erdosproblems/`.

## Fix

Add a Ruff exclude for the submodule path in `pyproject.toml`:

```toml
[tool.ruff]
extend-exclude = ["data/erdosproblems"]
```

Optionally, tighten CI to lint only `src/` + `tests/` instead of `.`.

## Related

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `data/erdosproblems/` (git submodule)
