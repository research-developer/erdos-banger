# DEBT-104: Error Type Naming Inconsistency

**Priority:** P4
**Status:** Fixed
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Found Commit:** 2082df5
**Fix Commit:** 0200a99

## Summary

`CLIOutput.error["type"]` values were inconsistent (e.g. `NotFound` vs `NotFoundError`), and several paths used overly-generic error types. This made downstream consumers and tests harder to reason about.

## Resolution

- Standardized "not found" outcomes to `NotFoundError`.
- Standardized timeouts to `TimeoutError`.
- Replaced generic `Error` with more specific categories where feasible (e.g. `UnexpectedError`, `LLMError`, `IngestError`, etc.).
- Updated tests asserting on the JSON contract.

## Verification

`error_type` distribution after the change:

```bash
rg -o --no-filename 'error_type=\"[^\"]*\"' src/erdos | sort | uniq -c | sort -rn | head
  33 error_type="UsageError"
  25 error_type="ConfigError"
  22 error_type="NotFoundError"
  17 error_type="UnexpectedError"
   9 error_type="IndexError"
   5 error_type="LoaderError"
   4 error_type="ZbMathError"
   4 error_type="NetworkError"
   4 error_type="LeanRunnerError"
   4 error_type="ExaError"
```

- `rg 'error_type="NotFound"' src/erdos` returns no matches.
- `make ci`

## Acceptance Criteria

- [x] No `NotFound` error types remain in `src/erdos/`
- [x] Tests updated for the new error type names
- [x] `make ci` passes
