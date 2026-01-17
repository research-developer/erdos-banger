# Bug: `iter_problems()` Allows Duplicate IDs (Index Overwrite Risk)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** (pending)

## Description

`ProblemLoader.load_all()` detected duplicate problem IDs and raised an error, but `ProblemLoader.iter_problems()` did not. Since `index_builder.build_index()` uses `iter_problems()`, duplicate IDs could silently overwrite earlier indexed rows.

## Steps to Reproduce

1. Create a YAML file with two problems sharing the same `id`.
2. Iterate with:
   - `list(ProblemLoader(path).iter_problems())`
3. (Optional) Build an index via `build_index()` or `erdos search --build-index`.

## Expected Behavior

Duplicate IDs are rejected consistently (both eager and lazy paths).

## Actual Behavior

`iter_problems()` yielded both problems without error.

## Root Cause

`iter_problems()` streamed parsed problems without tracking seen IDs.

## Fix

Track seen IDs during iteration and raise `ProblemLoaderError` on duplicates.

## Related

- `src/erdos/core/problem_loader.py`
- `src/erdos/core/index_builder.py`
- `tests/unit/test_problem_loader.py` (regression coverage)

