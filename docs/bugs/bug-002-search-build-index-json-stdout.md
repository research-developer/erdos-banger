# Bug: `erdos search --build-index --json` Contaminates stdout

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** e862a35

## Description

When `--json` and `--build-index` are used together, progress messages were printed to stdout before the JSON payload, producing invalid machine-readable output.

## Steps to Reproduce

1. Ensure a dataset is available (e.g., set `ERDOS_DATA_PATH`).
2. Run:
   - `uv run erdos search prime --build-index --json`

## Expected Behavior

stdout is valid JSON only.

## Actual Behavior

stdout begins with progress lines like:
- `Building search index...`
- `✓ Indexed N problems`
followed by JSON.

## Root Cause

`src/erdos/commands/search.py` printed build progress to the normal console even in JSON mode.

## Fix

When JSON mode is enabled, print build progress to stderr (or suppress it) so stdout remains pure JSON.

## Related

- `src/erdos/commands/search.py`
- `tests/integration/test_cli_commands.py` (regression coverage)
