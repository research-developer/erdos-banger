# Bug 008: Hardcoded Exit Code 78 Instead of ExitCode.CONFIG_ERROR

**Priority:** P0 (Critical)
**Status:** Open
**Found:** 2026-01-19
**Fixed:** —
**Commit:** —

## Description

The `ask_question()` function in `ask.py` returns exit code `78` when LLM command not found, but SPEC-011 specifies using `ExitCode.CONFIG_ERROR` which is defined as `10`.

## Files Affected

- `src/erdos/core/ask.py` (line ~247)
- `src/erdos/core/exit_codes.py` (defines `ExitCode.CONFIG_ERROR = 10`)

## Steps to Reproduce

```bash
# Unset LLM command
unset ERDOS_LLM_COMMAND
uv run erdos ask 6 "What is this problem about?"
echo $?  # Returns 78, should return 10
```

## Expected Behavior

Exit code should be `10` (`ExitCode.CONFIG_ERROR`) per SPEC-011 Section 3.2.

## Actual Behavior

Exit code is `78` (hardcoded magic number).

## Root Cause

Code was written before `ExitCode` enum was finalized:

```python
# src/erdos/core/ask.py line ~247
except FileNotFoundError:
    return CLIOutput.err(
        command="erdos ask",
        error_type="CONFIG_ERROR",
        message=f"LLM command not found: {llm_command}",
        code=78,  # WRONG: should be ExitCode.CONFIG_ERROR (10)
    )
```

## Fix

```python
from erdos.core.exit_codes import ExitCode

# Replace:
code=78,
# With:
code=ExitCode.CONFIG_ERROR,
```

## Related

- SPEC-011: `docs/specs/spec-011-ask-command.md`
- Exit codes: `src/erdos/core/exit_codes.py`
