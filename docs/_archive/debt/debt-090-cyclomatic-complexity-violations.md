# DEBT-090: Cyclomatic Complexity Violations (C901)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** 22f14f6

## Summary

Several functions exceeded Ruff’s default McCabe threshold (10) when audited ad-hoc with `ruff check --select C901`. While C901 is not enabled in CI, reducing complexity improves testability and readability.

## Resolution

- Extracted OpenAlex transformation logic into `src/erdos/core/clients/openalex_transform.py`.
- Reduced complexity in `src/erdos/core/run_logger.py` by extracting filter parsing/matching helpers.
- Loop iteration complexity is handled by DEBT-086 (iteration state machine split).

After refactors, ad-hoc complexity audit only flags the patch validator (which is intentionally kept; see DEBT-088).

## Verification

- `uv run ruff check --select C901 src/erdos/core` (only `validate_patch` remains)
- `make ci`

## Acceptance Criteria

- [x] `openalex_to_reference` complexity reduced below threshold
- [x] `RunLogger.query` complexity reduced below threshold
- [x] Loop runner complexity addressed (see DEBT-086)
- [x] `make ci` passes
