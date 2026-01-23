# DEBT-074: Test Quality Issues

**Status:** Open
**Priority:** P3 (Minor - improve when touching nearby code)
**Found:** 2026-01-23
**Found By:** Codebase audit (tests)

---

## Summary

Some test-quality issues that are style/design concerns, not correctness bugs. Tests function correctly but could be improved to better protect invariants.

---

## Verified Issues

### P3: Weak Uniqueness Test (Always Passes)

**File:** `tests/unit/batch/test_runner.py`

```python
def test_uniqueness(self) -> None:
    ids = {generate_batch_id() for _ in range(10)}
    assert len(ids) >= 1  # Always passes
```

**Issue:** Assertion `len(ids) >= 1` always passes when generating 10 IDs. This test doesn't verify uniqueness.

**Fix (example):**

```python
assert len(ids) >= 9, f"Expected mostly unique IDs, got {len(ids)}/10"
```

---

### P3: Tests Using `__new__` to Bypass Initialization

**File:** `tests/unit/core/test_lean_runner.py`

Some tests bypass `__init__` to call internal helpers directly:

```python
runner = LeanRunner.__new__(LeanRunner)
errors = runner._parse_errors(stderr)
```

**Issue:** Tests implementation details instead of behavior. This can be acceptable for parsing utilities, but consider exposing a public interface if the parsing logic becomes critical.

---

### P3: Tests Access Private Attributes

**File:** `tests/unit/core/test_problem_loader.py`

Tests assert on private attributes (e.g., `loader._cache`) instead of observable behavior.

---

## Proposed Fix

1. Fix the uniqueness assertion to meaningfully validate uniqueness.
2. (Optional) Refactor parsing helpers into pure functions (module-level) to make them testable without bypassing initialization.
3. (Optional) Prefer asserting observable behavior over private attributes for long-term test stability.

---

## Acceptance Criteria

1. Uniqueness tests use meaningful assertions.
2. `make ci` passes.
