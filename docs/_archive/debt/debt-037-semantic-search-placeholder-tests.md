# DEBT-037: Placeholder Semantic Search Tests (Always Pass)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-21
**Fixed:** 2026-01-21
**Commit:** b2dcdfe

---

## Summary

Two semantic search integration tests are effectively placeholders: they contain `pass` and therefore provide **zero regression value** when enabled. This is a “reward-hack” risk (tests appear to exist but do not test behavior).

## Evidence

File: `tests/integration/test_search_semantic.py`

Both tests are currently:
- marked `@pytest.mark.skipif(not NUMPY_AVAILABLE, ...)`
- implemented as `pass`

```python
def test_semantic_json_includes_semantic_score(...):
    pass

def test_hybrid_json_includes_all_scores(...):
    pass
```

## Why This Matters

- If `numpy` becomes available in CI/dev environments, these tests will run and trivially pass.
- They create a false sense of coverage around the `semantic_score` / `hybrid_score` JSON contract.

## Fix Options (3)

### Option A (Recommended): Implement deterministic assertions using the fake embedder

These tests already receive `fake_embedder`. Build embeddings/index deterministically and assert:
- semantic mode includes `semantic_score`
- hybrid mode includes `score`, `semantic_score`, `hybrid_score`

### Option B: Convert to `xfail` with a clear reason

If behavior is not yet stable, mark explicitly:
```python
@pytest.mark.xfail(reason="Semantic scores not yet emitted in JSON")
```
This prevents silent “pass” without assertions.

### Option C: Delete the tests until behavior exists

Remove the tests and re-add only once the feature is fully testable.

## Acceptance Criteria

1. [x] No tests in `tests/` contain bare `pass` without an explicit `xfail`/skip rationale.
2. [x] Semantic/hybrid search JSON contract is asserted deterministically in CI (no network).

---

## Resolution

These placeholder tests were replaced with deterministic assertions using the fake embedder boundary (no network required).
