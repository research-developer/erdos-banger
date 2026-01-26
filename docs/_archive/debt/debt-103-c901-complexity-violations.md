# DEBT-103: Untracked C901 Cyclomatic Complexity Violations

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Found Commit:** 2082df5
**Fix Commit:** 0200a99

## Summary

A code health audit surfaced functions exceeding Ruff's C901 cyclomatic complexity threshold (>10). While C901 is not enforced in the default Ruff configuration, the audit treats it as a maintainability gate.

## Resolution

Refactored the flagged functions to reduce branching:

- `src/erdos/lean_copilot/server.py:create_app` — extracted exception mapping helpers and reduced handler branching.
- `src/erdos/commands/sync/submodule_cmd.py:sync_submodule` — split into smaller helpers (`_sync_submodule_impl`, etc.).
- `src/erdos/core/clients/zbmath.py:ZbMathClient.get_by_zbl_id` — extracted caching/normalization helpers.
- `src/erdos/core/loop/patch_validator.py:validate_patch` — extracted `_validate_patch_size` to keep the validation pipeline readable and under threshold.

## Verification

- `uv run ruff check src/erdos --select=C901`
- `make ci`

## Acceptance Criteria

- [x] `uv run ruff check src/erdos --select=C901` passes
- [x] Refactors keep behavior unchanged
- [x] `make ci` passes
