# DEBT-087: LLM Execute Error Handling Consolidation

**Priority:** P3
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** 22f14f6

## Summary

`src/erdos/core/ask/llm.py::execute_llm_if_enabled()` previously:
- returned mixed types (`dict` on success, `CLIOutput` on error)
- hardcoded the command name in error paths
- duplicated exception-to-error mapping across branches

Even though guard clauses are acceptable, the mixed return types made call sites and tests more awkward.

## Resolution

- Introduced `LLMExecutionResult` (dataclass) as a consistent return type.
- Consolidated exception mapping in `_handle_llm_exception()`.
- Updated `execute_llm_if_enabled()` to require `command: str` and always return `LLMExecutionResult`.
- Updated ask service layer to consume the structured result.
- Updated unit tests accordingly.

## Verification

- `make ci`

## Acceptance Criteria

- [x] Consistent return type (no dict/CLIOutput mix)
- [x] No hardcoded `"erdos ask"` in shared helper (passed explicitly)
- [x] Exception mapping consolidated
- [x] `make ci` passes
