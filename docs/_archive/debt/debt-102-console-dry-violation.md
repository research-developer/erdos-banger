# DEBT-102: Console Instantiation DRY Violation

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Found Commit:** 2082df5
**Fix Commit:** (this PR)

## Summary

Multiple CLI command modules instantiated `rich.console.Console()` directly instead of using a shared SSOT. This created redundant configuration points and inconsistent stdout/stderr routing.

## Resolution

- Centralized `Console()` construction in `src/erdos/commands/presenter.py` as `console` and `err_console`.
- Replaced all command-local `Console()` instantiations with imports from `erdos.commands.presenter` (and `erdos.commands.presenter.err_console` where needed).

## Verification

- `rg "\\bConsole\\(" src/erdos` returns only `src/erdos/commands/presenter.py`.
- `make ci`

## Acceptance Criteria

- [x] Only `src/erdos/commands/presenter.py` instantiates `Console()`
- [x] Commands import `console` / `err_console` from `presenter`
- [x] `make ci` passes
