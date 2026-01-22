# DEBT-065: Command Layer Still Contains Application Logic (SRP Pressure)

**Status:** Fixed
**Priority:** P2
**Found:** 2026-01-22
**Fixed:** 2026-01-22
**Fixed In:** (pending commit)
**Found By:** Clean Code audit (SOLID principles review)

---

## Summary

Several command-layer entrypoints in `src/erdos/commands/` exceed the code-health guardrail `FUNCTION_LOC_THRESHOLD=120` and/or contain orchestration that belongs in the core bounded contexts (application/service layer). This creates SRP pressure:

1. Typer argument parsing
2. Calling service layer
3. Formatting output

In a CLI app, option-heavy signatures will always be "long"; the actionable part of this debt is **keeping application policy out of command modules** (and removing exemptions once the guardrail is satisfied).

---

## Resolution

Moved loop orchestration from `commands/loop.py::execute_loop()` to `core/loop/service.py::execute_proof_loop()`.

**Changes:**
1. Created `src/erdos/core/loop/service.py` with `execute_proof_loop()` function
2. Moved all orchestration logic (problem lookup, Lean project init, skeleton generation, loop execution, result mapping) to core
3. Refactored `commands/loop.py` to be a thin adapter that delegates to the core service
4. Removed stale DEBT-042 exemptions from audit script
5. Updated exemptions to reference DEBT-065 for remaining long functions

**Remaining long functions (Typer boilerplate, not business logic):**
- `commands/loop.py::run()` - 140 LOC (Typer options + docstring)
- `core/loop/runner.py::_run_single_iteration()` - 183 LOC (complex iteration logic)

These are exempted in the audit script and could be addressed in future decks if needed.

---

## Acceptance Criteria

1. [x] `commands/loop.py` no longer contains loop orchestration (Lean init/skeleton/runner setup)
2. [x] New core entrypoint exists in `src/erdos/core/loop/` (service/app module) returning `CLIOutput`
3. [x] `scripts/audit_code_health.py --strict` no longer reports `commands/loop.py:execute_loop` as an exempt long-function (deleted or reduced ≤ 120 LOC)
4. [x] CLI UX unchanged (`erdos loop --help` options and behavior preserved)
5. [x] All existing tests pass
6. [x] `make ci` passes

---

## Non-Goals

- Changing CLI UX or argument names
- Modifying JSON output format
- Changing loop semantics (Lean checks, patch validation, status mapping)
