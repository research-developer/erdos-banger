# Debt: Spec 005 Drift/Inconsistency

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** 19f2225

## Summary

`docs/specs/spec-005-problem-loader.md` contains outdated code samples and an internally inconsistent integration-testing section relative to the current implementation and upstream dataset reality.

## Details

- The spec states upstream `teorth/erdosproblems` `data/problems.yaml` is metadata-only, but also includes integration tests that attempt to load it as if it were enriched (titles/statements).
- The spec’s embedded `ProblemLoader` code sample does not reflect current hardenings in `src/erdos/core/problem_loader.py`:
  - duplicate ID detection in `load_all()`
  - explicit type validation for `tags` and `oeis_ids`
  - tags filter semantics treating `tags=[]` as “no filter”

## Impact

- Agents implementing from the spec may recreate previously fixed bugs.
- Spec readers may attempt “real upstream integration tests” that are impossible under the v1 “enriched-only” loader contract.

## Recommendation

Pick a single v1 stance and make Spec 005 match it:

1. **Enriched-only v1 (current code behavior):**
   - Remove/replace the “load upstream metadata-only YAML directly” integration test section.
   - Update code blocks to match current loader behavior and error messages.
   - Clearly separate “future enrichment pipeline” from v1 loader.

2. **Metadata-only upstream support (bigger scope):**
   - Define an enrichment/merge pipeline and adjust loader contracts accordingly.

## Related

- `docs/specs/spec-005-problem-loader.md`
- `src/erdos/core/problem_loader.py`
