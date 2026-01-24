# DEBT-082: Remove Unused Constants in `constants.py`

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-23
**Fix Commit:** 117d510

## Summary

Eight constants in `src/erdos/core/constants.py` were defined but never used. Keeping them created a misleading “available configuration” surface and made dead-code tooling noisy.

## Resolution

- Removed the unused constants from `src/erdos/core/constants.py`.
- Updated `tests/unit/core/test_constants.py` to assert only shipped constants and invariants.
- `make ci` passes.

## Acceptance Criteria

- [x] Remove all unused constants from `src/erdos/core/constants.py`
- [x] Tests updated appropriately
- [x] `make ci` passes
