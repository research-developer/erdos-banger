# Bug: `erdos search` Crashes When Index Exists but Dataset Is Missing

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** e862a35

## Description

If a populated search index exists but the source problems YAML cannot be located, `erdos search` crashed with an unhandled `ProblemLoaderError` instead of returning structured output.

## Steps to Reproduce

1. Build an index in a directory with a valid dataset:
   - `uv run erdos search prime --build-index`
2. Remove the dataset and run with the same index path:
   - `uv run erdos search prime --json`

## Expected Behavior

Either:
- The command still returns results (titles may be absent), or
- The command returns a clean, user-friendly error (and JSON stays valid with `--json`).

## Actual Behavior

The command crashed with a traceback and exited non-zero.

## Root Cause

`search_problems_fts()` attempted `ProblemLoader.from_default()` for title enrichment without handling missing datasets.

## Fix

Treat title enrichment as best-effort:
- If the loader is unavailable, still return index results (with `title: null`) instead of crashing.

## Related

- `src/erdos/commands/search.py`
- `tests/integration/test_cli_commands.py` (regression coverage)

