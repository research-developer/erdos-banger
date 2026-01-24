# DEBT-086: Loop Runner State Machine Refactor

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** 22f14f6

## Summary

The loop iteration logic previously lived as a large “state machine” in `core/loop/runner.py`, mixing:
- Lean check orchestration
- Prompt construction + LLM execution
- Patch validation + application + recording

This was correct but put avoidable SRP pressure on a single module and made the control-flow harder to evolve.

## Resolution

- Split the implementation into focused modules:
  - `src/erdos/core/loop/runner.py` now contains only `run_loop()` + small orchestration helpers.
  - `src/erdos/core/loop/iteration.py` contains `_IterationRunner` (the single-iteration state machine).
  - `src/erdos/core/loop/iteration_steps.py` contains small, testable helpers (Lean check/logging, prompt/logging, patch apply/record).
- Reduced control-flow complexity and eliminated the need for PLR0911 suppression in the iteration runner.
- Kept the public API stable (`erdos.core.loop.run_loop` unchanged; `erdos.core.loop.apply_patch` still available via re-export).

## Verification

- `make ci`
- `uv run python scripts/audit_code_health.py`

## Acceptance Criteria

- [x] Loop iteration code extracted from `runner.py`
- [x] Iteration state machine has ≤5 return points
- [x] No `scripts/audit_code_health.py` module-size violations
- [x] `make ci` passes
