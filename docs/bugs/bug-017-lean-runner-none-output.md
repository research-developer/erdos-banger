# Bug: stderr/stdout both None causes crash in lean_runner

**Priority:** P2
**Status:** Open
**Found:** 2026-01-21
**Fixed:** (pending)
**Commit:** (pending)

## Description

In `lean_runner.py`, the code assumes that at least one of `stderr` or `stdout` will be a non-None string. If both are `None` or empty, calling `.strip()` on the result of the `or` expression will raise `AttributeError`.

## Location

`src/erdos/core/lean_runner.py:219`

```python
raw = (result.stderr or result.stdout).strip()
```

## Steps to Reproduce

1. Mock `subprocess.run` to return a result where both `stderr` and `stdout` are `None`
2. Call the affected function
3. Observe `AttributeError: 'NoneType' object has no attribute 'strip'`

This could happen in edge cases where:
- The subprocess is killed before producing any output
- A very unusual Lean error occurs
- Platform-specific subprocess behavior differences

## Expected Behavior

Handle the case where both streams are None/empty gracefully:
- Return an empty error list, OR
- Return a generic "no output" error

## Actual Behavior

```
AttributeError: 'NoneType' object has no attribute 'strip'
```

## Root Cause

The `or` expression `(result.stderr or result.stdout)` returns `None` if both are falsy. The subsequent `.strip()` call assumes a string.

## Fix

Add a fallback for empty output:

```python
# Option 1: Default to empty string
raw = (result.stderr or result.stdout or "").strip()

# Option 2: Explicit check
output = result.stderr or result.stdout
if not output:
    return []  # or return [LeanError(file="", line=0, message="No output from Lean")]
raw = output.strip()
```

## Related

- Subprocess edge case handling
- Lean integration robustness
