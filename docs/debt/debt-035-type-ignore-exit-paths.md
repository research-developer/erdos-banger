# Technical Debt 035: type: ignore Suppressions in All Command Exit Paths

**Date:** 2026-01-21
**Status:** Open
**Priority:** P2 (Type safety gap)
**Impact:** Potential type mismatches hidden; harder to catch bugs during development

## Summary

All command modules have `# type: ignore[arg-type]` suppressions on their early-exit error paths when calling `exit_with_result()`.

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

The type mismatch is `Optional`-related:

- `get_app_context()` returns `(AppContext | None, CLIOutput | None)`.
- Commands use a combined guard like `if app_error is not None or app_ctx is None: ...`.
- mypy cannot prove `app_error` is non-None under that condition, so `exit_with_result(ctx, app_error)` is flagged.

## Acceptance Criteria

1. Investigate the actual type mismatch
2. Refactor the guard/flow so the error path passes a concrete `CLIOutput` (no `Optional`)
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
