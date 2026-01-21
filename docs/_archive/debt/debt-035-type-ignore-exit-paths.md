# Technical Debt 035: type: ignore Suppressions in All Command Exit Paths

**Date:** 2026-01-21
**Status:** Fixed
**Fixed In:** 86d3856
**Priority:** P2 (Type safety gap)
**Impact:** Potential type mismatches hidden; harder to catch bugs during development

## Summary

All command modules have `# type: ignore[arg-type]` suppressions on their early-exit error paths when calling `exit_with_result()`.

## Evidence

### Affected Files

| File | Line | Code |
|------|------|------|
| `src/erdos/commands/ingest.py` | 174 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `src/erdos/commands/show.py` | 124 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `src/erdos/commands/ask.py` | 187 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `src/erdos/commands/refs.py` | 108 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `src/erdos/commands/lean.py` | 307 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `src/erdos/commands/list_cmd.py` | 198 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |

### Related Suppressions

```python
# src/erdos/core/crossref_client.py:112
return response.json()  # type: ignore[no-any-return]
```

## Root Cause Analysis

The type mismatch is `Optional`-related:

- `get_app_context()` returns `(AppContext | None, CLIOutput | None)`.
- Commands use a combined guard like `if app_error is not None or app_ctx is None: ...`.
- mypy cannot prove `app_error` is non-None under that condition, so `exit_with_result(ctx, app_error)` is flagged.

## Solution

1. Changed `get_app_context()` return type from `tuple[AppContext | None, CLIOutput | None]` to `tuple[AppContext, None] | tuple[None, CLIOutput]` to express the true invariant: exactly one of context or error is non-None.

2. Refactored command guard pattern from:
   ```python
   if app_error is not None or app_ctx is None:
       exit_with_result(ctx, app_error)  # type: ignore[arg-type]
       return
   ```
   To:
   ```python
   if app_error is not None:
       exit_with_result(ctx, app_error)
       return
   if app_ctx is None:
       return  # Unreachable: get_app_context guarantees (ctx, None) or (None, error)
   ```

3. The separate `if app_ctx is None:` guard allows mypy to narrow `app_ctx` to non-None in subsequent code, while the first guard narrows `app_error` to `CLIOutput` (not `Optional[CLIOutput]`).

## Acceptance Criteria

1. ✅ Investigate the actual type mismatch
2. ✅ Refactor the guard/flow so the error path passes a concrete `CLIOutput` (no `Optional`)
3. ✅ All 6 `# type: ignore[arg-type]` removed
4. ✅ mypy passes with no errors
5. ✅ CI still passes (`make ci`)

## Files Modified

- `src/erdos/commands/app_context.py` - Changed return type to union of tuples
- `src/erdos/commands/show.py` - Refactored guard pattern
- `src/erdos/commands/ingest.py` - Refactored guard pattern
- `src/erdos/commands/ask.py` - Refactored guard pattern
- `src/erdos/commands/refs.py` - Refactored guard pattern
- `src/erdos/commands/lean.py` - Refactored guard pattern
- `src/erdos/commands/list_cmd.py` - Refactored guard pattern

## Related

- Strict mypy typing policy
- DEBT-016: SRP violation in domain models (previously fixed, may be related)
