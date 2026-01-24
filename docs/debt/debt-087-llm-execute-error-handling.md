# DEBT-087: LLM Execute Error Handling Consolidation

**Status:** Identified
**Created:** 2026-01-23
**Priority:** P3
**Tracking:** PLR0911 suppression in `core/ask/llm.py`

## Summary

`core/ask/llm.py::execute_llm_if_enabled()` has 7 return statements handling 4 exception types plus success/skip paths. While this uses guard clauses (which Uncle Bob approves), the function mixes result dict construction with exception handling.

## Current State

```python
def execute_llm_if_enabled(...):  # noqa: PLR0911
    result = {"answer": None, ...}  # Build result dict

    if not enable_llm:
        return result  # Return 1: disabled

    try:
        answer, exit_code = execute_llm(...)
    except FileNotFoundError:
        return CLIOutput.err(...)  # Return 2
    except subprocess.TimeoutExpired:
        return CLIOutput.err(...)  # Return 3
    except OSError:
        return CLIOutput.err(...)  # Return 4
    except ValueError:
        return CLIOutput.err(...)  # Return 5

    if exit_code != 0:
        return CLIOutput.err(...)  # Return 6

    result["answer"] = answer
    return result  # Return 7
```

## The Problem

1. **Mixed return types**: Returns `dict` on success, `CLIOutput` on error
2. **Hardcoded command name**: `"erdos ask"` in every error branch
3. **Exception handling repetition**: 4 nearly identical error construction blocks

## Recommended Refactor

### Option A: Result Type Pattern

```python
@dataclass
class LLMExecutionResult:
    answer: str | None = None
    exit_code: int | None = None
    error: CLIOutput | None = None

    @property
    def success(self) -> bool:
        return self.error is None

def execute_llm_if_enabled(...) -> LLMExecutionResult:
    if not enable_llm:
        return LLMExecutionResult()  # Empty success (disabled)

    error = _try_execute_llm(llm_command, prompt)
    if error:
        return LLMExecutionResult(error=error)

    return LLMExecutionResult(answer=answer, exit_code=exit_code)
```

### Option B: Exception Mapping

```python
_LLM_EXCEPTION_MAP = {
    FileNotFoundError: ("CONFIG_ERROR", "LLM command not found"),
    subprocess.TimeoutExpired: ("TIMEOUT", "LLM command timed out"),
    OSError: ("CONFIG_ERROR", "LLM command error"),
    ValueError: ("CONFIG_ERROR", "Invalid LLM command syntax"),
}

def _handle_llm_exception(e: Exception, command: str) -> CLIOutput:
    error_type, message_template = _LLM_EXCEPTION_MAP.get(
        type(e), ("ERROR", "Unknown error")
    )
    return CLIOutput.err(command=command, error_type=error_type, message=...)
```

## Acceptance Criteria

- [ ] Extract exception handling into helper or use mapping
- [ ] Use consistent return type (Result object or tuple)
- [ ] Remove hardcoded `"erdos ask"` (pass as parameter)
- [ ] Remove PLR0911 suppression
- [ ] Maintain 100% test coverage

## Impact

- **Low risk**: This is internal plumbing, not public API
- **Low effort**: ~30 minutes of refactoring
- **High clarity gain**: Cleaner error handling pattern
