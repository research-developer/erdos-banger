# Bug: Silent exception swallowing masks errors

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-21
**Fixed:** 2026-01-21
**Commit:** 1d5bd51

## Description

Multiple exception handlers in the codebase caught exceptions and either `pass`ed silently or converted failures to `None` without any logging. This made debugging difficult and masked real errors.

## Affected Locations

The following locations were updated to log before continuing in best-effort paths:

- `src/erdos/core/problem_loader.py` (package dataset fallback)
- `src/erdos/core/lean_runner.py` (Lean version probe)
- `src/erdos/core/arxiv_client.py` (published date parsing)

Additionally, search result enrichment already logs at debug level when enrichment fails (best-effort behavior).

## Expected Behavior

- Errors should be logged before being handled in best-effort paths.
- Callers/operators should be able to distinguish “not found” from “error” when appropriate.

## Fix

Best-effort fallbacks now log at appropriate levels:
- Debug logs for recoverable probe/parse failures
- Warning logs for manifest corruption (see BUG-016)

## Related

- BUG-016: Manifest corruption silently returns None (fixed)
