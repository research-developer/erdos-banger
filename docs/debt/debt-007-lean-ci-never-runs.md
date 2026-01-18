# DEBT-007: Lean Compilation Never Actually Tested in CI

**Priority:** P1
**Status:** Open
**Found:** 2026-01-18
**Affects:** Lean integration, CI pipeline, `erdos lean` commands

## Problem

CI has a `test-with-lean` job that appears to test Lean integration, but:
1. The job explicitly handles "no tests collected" as success (exit code 5)
2. Only 1 test class is marked `@pytest.mark.requires_lean`
3. That test class is also marked `@pytest.mark.skipif(not lean_available)`
4. We've never actually compiled a Lean file in CI

The entire Lean compilation pipeline could be broken and CI would still pass.

## Evidence

**CI configuration (`.github/workflows/ci.yml:105-114`):**
```yaml
- name: Run Lean-dependent tests
  run: |
    set +e
    uv run pytest -m "requires_lean"
    status=$?
    if [ $status -eq 5 ]; then
      echo "No tests collected for marker 'requires_lean'; skipping."
      exit 0
    fi
    exit $status
```

**Only Lean-marked test (`tests/integration/test_lean_runner.py:20-21`):**
```python
@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
class TestLeanRunnerIntegration:
```

**Local verification:**
```bash
$ which lake
# (no output - not installed)

$ which lean
# (no output - not installed)
```

**Result:** The test is double-skipped:
- First by pytest marker filtering (only `requires_lean` tests selected)
- Then by skipif (lean not available)
- Then CI treats "no tests collected" as success

## Risk

- `erdos lean check` could be completely broken
- `erdos lean init` could generate invalid Lean projects
- Template syntax errors would go undetected
- Lean 4 compatibility issues would surface only for real users
- The "autonomous solver" vision requires working Lean compilation

## Proposed Resolution

1. **Option A: Actually install Lean in CI**
   - Remove the `skipif` decorator OR
   - Ensure elan installation happens before pytest runs
   - Verify `lake` and `lean` are on PATH

2. **Option B: Add a "compile check" step**
   - After installing elan, run `lake build` on `formal/lean/`
   - Separate from Python tests, guarantees Lean toolchain works

3. **Option C: Mock-based verification (minimum)**
   - Test that generated Lean files are syntactically valid
   - Use `lean --version` check as smoke test

## Acceptance Criteria

- [ ] CI actually runs at least one Lean compilation
- [ ] A syntax error in Lean templates would cause CI to fail
- [ ] `lake build` succeeds on the `formal/lean/` project in CI
- [ ] Test output shows "Lean tests: X passed" (not "skipped" or "no tests collected")
