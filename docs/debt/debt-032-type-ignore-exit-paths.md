# Technical Debt 032: type: ignore Suppressions in All Command Exit Paths

**Date:** 2026-01-21
**Status:** Open
**Priority:** P2 (Type safety gap)
**Impact:** Potential type mismatches hidden; harder to catch bugs during development

## Summary

All command modules have `# type: ignore[arg-type]` suppressions on their error exit paths when calling `exit_with_result()`. This suggests a systematic type mismatch between `CLIOutput` construction and the `exit_with_result` function signature.

## Evidence

### Affected Files

| File | Line | Code |
|------|------|------|
| `commands/ingest.py` | 174 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `commands/show.py` | 119 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `commands/ask.py` | 187 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `commands/refs.py` | 103 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `commands/lean.py` | 294 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |
| `commands/list_cmd.py` | 193 | `exit_with_result(ctx, app_error)  # type: ignore[arg-type]` |

### Related Suppressions

```python
# crossref_client.py:112
return response.json()  # type: ignore[no-any-return]
```

## Root Cause Analysis

The `exit_with_result` function likely has a signature expecting a specific type, but error paths construct `CLIOutput` in a way that doesn't match. Possible causes:

1. `CLIOutput.err()` returns a different type than `CLIOutput.ok()`
2. Union type narrowing not working correctly
3. Generic type parameters not properly constrained

## Acceptance Criteria

1. Investigate the actual type mismatch
2. Fix the function signatures or type annotations to eliminate the suppressions
3. All 6 `# type: ignore[arg-type]` removed
4. mypy passes with no errors
5. CI still passes (`make ci`)

## Investigation Steps

1. Check `exit_with_result` signature in `presenter.py`
2. Check `CLIOutput.err()` return type
3. Check if `app_error` variable type differs from expected
4. Consider if Optional/Union types need adjustment

## Related

- Strict mypy typing policy
- DEBT-016: SRP violation in domain models (previously fixed, may be related)
