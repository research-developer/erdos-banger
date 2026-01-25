# DEBT-105: Print Statements in Core Modules

**Priority:** P4
**Status:** Resolved (audit false positive)
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Found Commit:** 2082df5
**Fix Commit:** (this PR)

## Summary

An audit grepping for `print(` under `src/erdos/core/` flagged a few occurrences, but they were inside docstring examples (not executable code). Runtime code already uses logging consistently.

## Resolution

- Updated docstring examples to avoid `print(...)` so grep-based audits don't report false positives.

## Evidence

- `src/erdos/core/lean/aristotle.py`: replaced docstring example `print(...)` with `logger.info(...)`
- `src/erdos/core/lean/runner.py`: replaced docstring example `print(error)` with `logger.warning(...)`
- `src/erdos/core/timing.py`: replaced docstring example `print(...)` with assignment (`took_ms = ...`)

## Verification

- `rg -n '(^|[^.])\bprint\(' src/erdos/core` returns no matches.
- `make ci`

## Acceptance Criteria

- [x] No runtime `print()` calls remain in `src/erdos/core/`
- [x] `make ci` passes
