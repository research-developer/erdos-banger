# DEBT-098: Test References Deprecated std4 Repository

**Status:** Fixed
**Priority:** P1 (causes CI failure)
**Created:** 2026-01-24
**Fixed:** 2026-01-24
**Commit:** e49696e
**Related:** `test-with-lean` CI job failure

## Problem

The test `test_clone_and_verify_real_repo` in `tests/integration/test_sync_proof.py` references the `leanprover/std4` repository, which has been renamed to `leanprover-community/batteries`.

## Evidence

```python
# tests/integration/test_sync_proof.py:205-219
result = clone_repository(
    "https://github.com/leanprover-community/batteries",
    tmp_path / "batteries",
    timeout=120,
    depth=1,
)

assert (tmp_path / "batteries").exists()
assert (tmp_path / "batteries" / "lakefile.toml").exists()
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

Implemented Option A (update to batteries).

## Acceptance Criteria

1. [x] Update test to use correct repository URL
2. [x] Verify test passes (`make ci` / `make test-all` with Lean)
3. [ ] Consider using a stable, dedicated test repo for proof verification tests
