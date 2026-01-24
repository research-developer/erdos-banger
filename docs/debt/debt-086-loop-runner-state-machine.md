# DEBT-086: Loop Runner State Machine Refactor

**Status:** Identified
**Created:** 2026-01-23
**Author:** Claude (Uncle Bob analysis)
**Tracking:** DEBT-065 (exemption)

## Summary

`core/loop/runner.py::_run_single_iteration()` is 183 LOC with 11 return points. While the code works and is readable, it violates the Single Responsibility Principle by mixing orchestration, LLM interaction, and patch application concerns.

## Current State

```
src/erdos/core/loop/runner.py:191 _run_single_iteration(): 183 LOC (threshold: 120)
11 return statements (PLR0911 suppressed)
```

The function currently:
1. Reads file state
2. Runs Lean check
3. Checks completion condition
4. Builds prompt and calls LLM
5. Handles LLM errors
6. Validates patch
7. Handles rejected patches
8. Applies patch (or skips in no-apply mode)
9. Verifies applied patch
10. Records iteration
11. Checks for final completion

## Why This Matters

- **Testing:** To unit test LLM interaction, you must mock the entire iteration
- **Modification:** Changing LLM behavior requires understanding the full state machine
- **Readability:** 11 return points make control flow analysis difficult

## Recommended Refactor

Extract three focused helpers:

```python
def _call_llm_and_get_patch(
    file_path: Path,
    problem: ProblemRecord,
    last_check: LeanCheckResult,
    config: LoopConfig,
    llm_command: str,
    rag_chunks: list,
    loop_logger: LoopLogger,
    iteration: int,
) -> LLMResult:
    """Build prompt, call LLM, return structured result."""
    ...

def _apply_and_record_patch(
    file_path: Path,
    patch: ValidatedPatch,
    config: LoopConfig,
    loop_logger: LoopLogger,
    iteration: int,
) -> PatchApplicationResult:
    """Apply patch, verify, return result."""
    ...

def _run_single_iteration(...) -> IterationResult:
    """Orchestrate one iteration using focused helpers."""
    # Now ~60 LOC: check -> call LLM -> apply patch -> return
    ...
```

## When to Refactor

**Refactor WHEN:**
- You need to modify LLM calling behavior
- You need to modify patch application logic
- You're adding new exit conditions

**Don't refactor just to satisfy the metric** - the code works and is well-tested.

## Acceptance Criteria

- [ ] Extract `_call_llm_and_get_patch()` helper
- [ ] Extract `_apply_and_record_patch()` helper
- [ ] Reduce `_run_single_iteration` to <80 LOC
- [ ] Reduce return points to ≤5
- [ ] Maintain 100% test coverage for affected paths
- [ ] Remove PLR0911 suppression

## Boy Scout Rule

Apply this refactor when you next touch `loop/runner.py` for a feature or bug fix. Don't create a standalone refactor PR just for this.

---

## NOT Technical Debt (False Positives)

The following exemptions are **not** technical debt - they are metric artifacts:

### Typer Command Functions

| Function | LOC | Actual Logic |
|----------|-----|--------------|
| `commands/convert.py::convert()` | 171 | ~40 LOC |
| `commands/ingest.py::ingest()` | 157 | ~45 LOC |
| `commands/loop.py::run()` | 145 | ~37 LOC |
| `commands/search.py::search()` | 140 | ~35 LOC |

These functions are long because of:
- Typer `Annotated[..., typer.Option(...)]` declarations (~8 lines per option)
- Comprehensive docstrings with examples (~25 lines)
- The actual business logic is <50 LOC each

**Uncle Bob says:** "The function does ONE thing: accept CLI arguments and delegate. The 'size' is interface declaration, not complexity."

### `ingest_problem_references()` (147 LOC)

This is **linear orchestration** - each step is a single helper call:
```python
problem, error = _load_problem(...)
manifest = _load_existing_manifest(...)
result = process_all_references(...)
# etc.
```

The docstring correctly notes: "pure linear orchestration with no branching complexity."

**Uncle Bob says:** "This is well-factored. Don't split for the sake of splitting."
