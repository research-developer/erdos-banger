# Technical Debt 012: Broad Exception Handling in ingest.py

**Date:** 2026-01-19
**Status:** Fixed
**Priority:** P1
**Impact:** Masks real bugs, makes debugging difficult
**Fixed:** 2026-01-19
**Commit:** 2cb6fac

## Problem

Multiple `except Exception as e` blocks in `ingest.py` catch all exceptions indiscriminately:

```python
# Line 78-84
try:
    loader = ProblemLoader.from_default()
    problem = loader.get_by_id(problem_id)
    if problem is None:
        return CLIOutput.err(...)
except Exception as e:  # TOO BROAD
    return CLIOutput.err(
        command="ingest",
        error_type="NotFoundError",  # Misleading
        message=f"Problem {problem_id} not found: {e}",
        code=ExitCode.NOT_FOUND,
    )
```

This catches:
- `FileNotFoundError` (expected)
- `yaml.YAMLError` (config issue)
- `requests.Timeout` (network issue)
- `AttributeError` (real bug)
- `TypeError` (real bug)

All are treated as "NotFoundError" which is incorrect.

## Impact

1. **Test failures masked** - Real bugs look like expected errors
2. **Wrong exit codes** - Network errors return NOT_FOUND instead of NETWORK_ERROR
3. **Poor error messages** - Users can't distinguish problems

## Locations

- `src/erdos/core/ingest.py` lines 78-84, 98-100, 143-157
- Similar pattern may exist in other modules

## Fix

Catch specific exceptions:

```python
except FileNotFoundError as e:
    return CLIOutput.err(..., error_type="NotFoundError", code=ExitCode.NOT_FOUND)
except ValueError as e:  # YAML parsing
    return CLIOutput.err(..., error_type="ConfigError", code=ExitCode.CONFIG_ERROR)
except requests.Timeout as e:
    return CLIOutput.err(..., error_type="NetworkError", code=ExitCode.NETWORK_ERROR)
except requests.HTTPError as e:
    if e.response.status_code == 404:
        # Handle gracefully per-reference
    else:
        return CLIOutput.err(..., error_type="NetworkError", ...)
```

## Related

- SPEC-010 Section 5.0: "tests must exercise HTTP error paths deterministically"
- BUG-008: Exit code inconsistency (related pattern)
