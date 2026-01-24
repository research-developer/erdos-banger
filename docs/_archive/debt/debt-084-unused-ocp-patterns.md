# DEBT-084: Finish Batch Interrupt Wiring (and validate summarizer hook)

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-23
**Fix Commit:** 117d510

## Summary

This deck started as a “dead code / YAGNI” suspicion, but validation showed:

- `register_summarizer()` is intentionally supported and already tested; it is not dead code.
- `BatchRunner.interrupt()` existed, but nothing invoked it, so batch Ctrl+C behavior did not meet Spec-015 (“graceful shutdown, second Ctrl+C exits immediately”).

## Resolution

- Implemented SIGINT handling in `BatchRunner`:
  - First Ctrl+C requests a graceful stop after the current problem.
  - Second Ctrl+C raises `KeyboardInterrupt` immediately.
- Added a unit test proving `interrupt()` stops the runner after the current problem.
- Kept `register_summarizer()` as a supported extension hook for run-log summaries.

## Acceptance Criteria

- [x] Batch interrupt is wired and test-covered
- [x] No removals of intentional extension points
- [x] `make ci` passes
