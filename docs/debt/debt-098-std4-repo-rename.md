# DEBT-098: Test References Deprecated std4 Repository

**Status:** Open
**Priority:** High (causes CI failure)
**Created:** 2026-01-24
**Related:** `test-with-lean` CI job failure

## Problem

The test `test_clone_and_verify_real_repo` in `tests/integration/test_sync_proof.py` references the `leanprover/std4` repository, which has been renamed to `leanprover-community/batteries`.

## Evidence

```python
# tests/integration/test_sync_proof.py:205-219
result = clone_repository(
    "https://github.com/leanprover/std4",  # DEPRECATED URL
    tmp_path / "std4",
    timeout=120,
    depth=1,
)

assert (tmp_path / "std4").exists()
assert (tmp_path / "std4" / "lakefile.lean").exists()  # FAILS
```

CI Error:
```
E   AssertionError: assert False
E    +  where False = exists()
E    +    where exists = ((PosixPath('.../test_clone_and_verify_real_rep0') / 'std4') / 'lakefile.lean').exists
```

## Root Cause

1. GitHub redirects `leanprover/std4` → `leanprover-community/batteries`
2. Git clone may use the redirected repo name or the original depending on behavior
3. The `lakefile.lean` structure may have changed in the renamed repo

## Impact

- **CI Failure:** The `test-with-lean` job fails on every PR
- **False Signal:** Makes it hard to identify real regressions

## Fix Options

### Option A: Update to batteries (Recommended)
```python
result = clone_repository(
    "https://github.com/leanprover-community/batteries",
    tmp_path / "batteries",
    timeout=120,
    depth=1,
)
assert (tmp_path / "batteries" / "lakefile.toml").exists()  # Note: may use .toml now
```

### Option B: Use a smaller, more stable test repo
Create a dedicated test fixture repo under the org that won't change.

### Option C: Skip the test
Mark as `@pytest.mark.skip(reason="DEBT-098: std4 renamed to batteries")` until fixed.

## Acceptance Criteria

1. [ ] Update test to use correct repository URL
2. [ ] Verify test passes in CI
3. [ ] Consider using a stable, dedicated test repo for proof verification tests

## Effort Estimate

~30 minutes for Option A, ~2 hours for Option B.
