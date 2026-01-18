# DEBT-007: Lean Compilation Success Not Enforced in CI

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-18
**Fixed:** 2026-01-18
**Commit:** c9cbf24,ec0b93d
**Affects:** Lean integration, CI pipeline, `erdos lean` commands

## Resolution

- CI `test-with-lean` now runs `lake update` + `lake build` in `formal/lean/` before Python tests.
- Added an integration test that asserts `LeanRunner.check()` successfully compiles `formal/lean/Erdos/Basic.lean` when Lean is available.

## Problem (before fix)

CI has a `test-with-lean` job that appears to test Lean integration, but the current signal is weaker than it looks:
1. The job explicitly treats "no tests collected" as success (exit code 5)
2. Only 1 test class is marked `@pytest.mark.requires_lean`
3. That test class is also gated by `lean_available = shutil.which("lean") is not None`
4. The "valid file" test does not assert successful compilation (it only asserts the runner returns a result without raising)

As a result, Lean compilation failures can slip through without CI failing (especially failures that return a non-success result rather than raising).

## Evidence (before fix)

**CI configuration (`.github/workflows/ci.yml:112-121`):**
```yaml
      - name: Run Lean-dependent tests
        run: |
          set +e
          uv run --frozen pytest -m "requires_lean"
          status=$?
          if [ $status -eq 5 ]; then
            echo "No tests collected for marker 'requires_lean'; skipping."
            exit 0
          fi
          exit $status
```

**Only Lean-marked test suite (`tests/integration/test_lean_runner.py:17-22`):**
```python
lean_available = shutil.which("lean") is not None


@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
class TestLeanRunnerIntegration:
```

**"Valid file" test does not assert compilation success (`tests/integration/test_lean_runner.py:33-44`):**
```python
    def test_check_valid_file(self, tmp_path: Path) -> None:
        """check succeeds on valid Lean file."""
        runner = LeanRunner(tmp_path)
        runner.init(fetch_mathlib=False)

        test_file = tmp_path / "Erdos" / "Test.lean"
        test_file.write_text("theorem simple : 1 + 1 = 2 := rfl\n", encoding="utf-8")

        result = runner.check(test_file)

        # May fail without mathlib, but should not raise
        assert result.file == "Erdos/Test.lean"
```

**Result:** The job can pass without enforcing "Lean compilation works end-to-end":
- If `requires_lean` tests disappear or are mis-marked, CI treats "no tests collected" as success
- If `lean` isn't on PATH, the only `requires_lean` suite is skipped
- Even when `lean` is on PATH, the "valid file" test does not assert `result.success`

## Risk

- `erdos lean check` could be completely broken
- `erdos lean init` could generate invalid Lean projects
- Template syntax errors would go undetected
- Lean 4 compatibility issues would surface only for real users
- The "autonomous solver" vision requires working Lean compilation

## Proposed Resolution

1. **Option A: Make Lean availability explicit in CI**
   - Add an explicit `lean --version` (or `elan show`) step before pytest
   - Fail fast if `lean`/`lake` are missing from PATH
   - Keep the `skipif` gate only for local dev environments

2. **Option B: Add a "compile check" step**
   - After installing elan, run `lake build` on `formal/lean/`
   - Separate from Python tests, guarantees Lean toolchain works

3. **Option C: Strengthen the Python tests (minimum)**
   - Assert `result.success` for at least one "valid file" check
   - Distinguish "Lean not available" from "Lean compiled and returned errors"

## Acceptance Criteria

- [ ] CI actually runs at least one Lean compilation
- [ ] A syntax error in Lean templates would cause CI to fail
- [ ] `lake build` succeeds on the `formal/lean/` project in CI
- [ ] Test output shows "Lean tests: X passed" (not "skipped" or "no tests collected")
