# DEBT-088: Patch Validator Multiple Returns

**Status:** Won't Fix (validated)
**Created:** 2026-01-23
**Priority:** P4
**Tracking:** PLR0911 suppression in `core/loop/patch_validator.py`

## Summary

`core/loop/patch_validator.py::validate_patch()` has 11 return statements across a validation pipeline. Unlike DEBT-086 and DEBT-087, this is actually a **reasonable pattern** for validation code.

## Current State

```python
def validate_patch(...):  # noqa: PLR0911
    # 1. Check for explicit "no fix" response
    if response.strip() == "NO_FIX_POSSIBLE":
        return PatchResult.no_fix()

    # 2. Parse SEARCH/REPLACE block
    parsed = parse_search_replace(response)
    if parsed is None:
        return PatchResult.reject("No valid SEARCH/REPLACE block found")

    # 3. Size validation (bytes)
    if len(replace_text.encode("utf-8")) > config.max_patch_bytes:
        return PatchResult.reject(...)

    # 4. Size validation (lines)
    # 5. Path validation (security)
    # 6. Find match in target file
    # 7. Check for placeholder injection
    # 8. Syntax sanity check

    return PatchResult.ok(...)
```

## Analysis

**Why this is ACCEPTABLE:**

1. **Single Responsibility**: The function does ONE thing (validate a patch)
2. **Guard Clause Pattern**: Each return is a guard for one validation
3. **Pure Function**: No side effects, just returns result
4. **Early Exit**: Saves computation by failing fast
5. **Readable**: Each validation step is clearly labeled with comments

**Why the alternative is WORSE:**

```python
# DON'T DO THIS - it's harder to read
def validate_patch(...):
    errors = []
    if response.strip() == "NO_FIX_POSSIBLE":
        return PatchResult.no_fix()
    parsed = parse_search_replace(response)
    if parsed is None:
        errors.append("No valid block")
    elif len(replace_text.encode()) > config.max_patch_bytes:
        errors.append("Too many bytes")
    elif ...

    if errors:
        return PatchResult.reject(errors[0])
    return PatchResult.ok(...)
```

This loses:
- Early exit (all validations run even after first failure)
- Clarity (nested conditionals)
- Correctness (some checks depend on earlier checks passing)

## Decision

**Keep the current code.** The PLR0911 suppression is justified.

Add a comment explaining why:

```python
def validate_patch(  # noqa: PLR0911 - validation pipeline with early exits
    response: str, target_file: Path, config: LoopConfig
) -> PatchResult:
```

## Optional Improvement (Non-blocking)

- [ ] Add an inline comment explaining why PLR0911 is justified

## Verdict

**NOT TECHNICAL DEBT** - This is an acceptable validation pattern. The PLR0911 lint is a false positive for this use case.
