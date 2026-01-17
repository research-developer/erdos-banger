# Debt: Spec 008 Fixtures Are Incomplete

**Priority:** P1
**Status:** Open
**Found:** 2026-01-17

## Summary

The repository’s `tests/fixtures/` directory does not include several files that Spec 008 declares as required fixtures.

## Current State

Present:
- `tests/fixtures/sample_problems.yaml` (3 problems)
- `.gitkeep` placeholders in `tests/fixtures/crossref_responses/`, `tests/fixtures/arxiv_responses/`, `tests/fixtures/lean_outputs/`

Missing (per spec):
- `tests/fixtures/__init__.py`
- `tests/fixtures/single_problem.yaml`
- `tests/fixtures/invalid_problems.yaml`
- Recorded Crossref JSON and arXiv XML samples
- Lean output fixtures (`successful_compile.txt`, etc.)
- Expanded `sample_problems.yaml` dataset (spec example shows 6 problems)

## Impact

Future specs (network ingestion, Lean parsing) and their tests cannot be implemented literally from Spec 008 without first adding these fixtures or updating the spec.

## Recommendation

Either:
1. Add the missing fixture files exactly as Spec 008 defines, or
2. Update Spec 008 to match the intended minimal v1 fixture set and adjust downstream specs accordingly.

## Related

- `docs/specs/spec-008-test-fixtures.md`
- `tests/fixtures/`

