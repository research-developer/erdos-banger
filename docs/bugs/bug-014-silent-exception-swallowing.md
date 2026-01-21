# Bug: Silent exception swallowing masks errors

**Priority:** P1
**Status:** Open
**Found:** 2026-01-21
**Fixed:** (pending)
**Commit:** (pending)

## Description

Multiple exception handlers in the codebase catch exceptions and either `pass` silently or convert to `None` without any logging or indication of what failed. This makes debugging extremely difficult and masks real errors.

## Affected Locations

### 1. `src/erdos/core/problem_loader.py:97-98`

```python
except (ImportError, TypeError, AttributeError, FileNotFoundError):
    pass  # Silent swallow - no indication of what failed
```

**Impact:** Package data loading failures are completely invisible. If the fallback chain silently skips a step, operators have no way to know.

### 2. `src/erdos/core/lean_runner.py:93-94`

```python
except (subprocess.TimeoutExpired, FileNotFoundError):
    pass  # Timeout and missing Lean silently ignored
```

**Impact:** `lean_version` remains unset if Lean is not installed or times out. Code continues without any indication of the problem.

### 3. `src/erdos/core/arxiv_client.py:82-83`

```python
except (ValueError, AttributeError):
    pass  # Year is optional, continue without it
```

**Impact:** Date parsing errors are silently swallowed. While the comment says "year is optional", malformed dates from arXiv should at least be logged for data quality tracking.

### 4. `src/erdos/commands/search.py:118-119`

```python
except Exception:              # Bare Exception catch
    problem = None             # Sets to None, no logging
```

**Impact:** Any error during problem lookup (database error, validation error, etc.) is silently converted to `None`. Caller cannot distinguish "not found" from "error occurred".

## Expected Behavior

- Errors should be logged before being handled
- Callers should be able to distinguish "not found" from "error"
- At minimum, a debug-level log should indicate what exception was caught

## Actual Behavior

- Exceptions are silently swallowed
- No audit trail exists
- Debugging production issues is nearly impossible

## Root Cause

Defensive coding taken too far. The intent was to make the code resilient, but without logging, the resilience becomes opacity.

## Fix

For each location:

1. Add logging before the `pass` or `return None`:
   ```python
   except (ImportError, TypeError, AttributeError, FileNotFoundError) as e:
       logger.debug("Package data loading skipped: %s", e)
       pass  # Continue to next fallback
   ```

2. For bare `except Exception`, narrow the exception type and log:
   ```python
   except (KeyError, ValueError) as e:
       logger.warning("Problem lookup failed for ID %d: %s", r.problem_id, e)
       problem = None
   ```

## Related

- DEBT-026: No logging framework usage in codebase
- DEBT-012: Broad exception handling in ingest.py (previously fixed, but similar pattern remains)
