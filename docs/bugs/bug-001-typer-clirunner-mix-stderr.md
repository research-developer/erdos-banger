# Bug: Typer `CliRunner` Unsupported `mix_stderr` Arg

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** e862a35

## Description

`pytest` failed during test collection because `typer.testing.CliRunner` (via Click) does not accept a `mix_stderr` argument in its constructor.

## Steps to Reproduce

1. Run:
   - `uv run pytest -m "not requires_lean and not requires_network"`

## Expected Behavior

Tests collect and run normally.

## Actual Behavior

Test collection crashes with:
- `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'`

## Root Cause

`tests/integration/test_cli_commands.py` instantiated `CliRunner(mix_stderr=False)` but Click's `CliRunner.__init__` signature does not include `mix_stderr`.

## Fix

Instantiate `CliRunner()` without the unsupported argument.

## Related

- `tests/integration/test_cli_commands.py`
