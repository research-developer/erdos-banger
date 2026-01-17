# Debt: Placeholder Tests vs Real Coverage

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** 59bdeac

## Summary

The test suite still includes “placeholder” tests intended to bootstrap CI/test structure (per Spec 002). They provide limited regression value and should be replaced as real features land.

## Examples

- `tests/unit/test_placeholder.py`
- `tests/integration/test_placeholder.py`
- `tests/e2e/test_placeholder.py`

## Impact

- Inflates test counts without materially improving confidence.
- Can mask areas where real behavior lacks coverage.

## Recommendation

As each command/module gains real tests:
- Delete the corresponding placeholder test file.
- Replace with behavior-driven tests that assert user-visible outputs and error paths.

## Related

- `docs/specs/spec-002-testing-strategy.md`
- `tests/`
