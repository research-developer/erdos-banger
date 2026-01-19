# Bug 011: No Enriched Problem Data for Production Use

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-19
**Fixed:** 2026-01-19
**Commit:** 54e2dfb

## Description

On a fresh clone, `erdos list` failed immediately because the default loader fell back to the upstream
`teorth/erdosproblems` dataset (`data/erdosproblems/data/problems.yaml`), which is **metadata-only**
and intentionally rejected by the v1 `ProblemLoader` (it lacks `id`, `title`, `statement`).

This created a bad first-run experience: the repo *looked* like it included data (submodule present),
but the CLI couldn’t run unless the user manually created `data/problems_enriched.yaml`.

## Steps to Reproduce

```bash
uv run erdos list
```

## Expected Behavior

The CLI should run out of the box and list problems using a valid dataset (at minimum, a built-in sample dataset).

## Actual Behavior

```
Error: Failed to parse 1135 problems:
Problem at index 0: Unsupported upstream teorth/erdosproblems format
(metadata-only). v1 requires enriched problems with id/title/statement.
```

## Root Cause

1. `ProblemLoader.from_default()` checked `./data/erdosproblems/data/problems.yaml` **before** any packaged sample dataset fallback.
2. `_parse_problem()` rejects the upstream schema by design, so parsing fails for every entry.
3. `ERDOS_DATA_PATH` only accepted a directory, not a direct YAML file path, which made ad-hoc overrides harder.

## Impact

- All CLI commands fail out of the box after fresh clone
- Users cannot use the tool without manually creating enriched data
- Tests and CI masked the first-run failure by always providing an explicit fixture dataset.

## Related

- Spec 005: Problem Loader
- `src/erdos/core/problem_loader.py:52-96` (path resolution logic)

## Fix

1. Added a built-in sample dataset at `src/erdos/data/problems_enriched.yaml`.
2. Updated `ProblemLoader.from_default()`:
   - `ERDOS_DATA_PATH` supports both file and directory paths.
   - Packaged sample dataset is preferred before the upstream metadata-only dataset.
3. Updated tests to assert the packaged fallback and to stop assuming titles are unavailable when the dataset is missing.
