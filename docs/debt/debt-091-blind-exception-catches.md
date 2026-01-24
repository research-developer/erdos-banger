# DEBT-091: Blind Exception Catches (BLE001)

**Status:** Identified
**Created:** 2026-01-23
**Priority:** P3
**Found By:** Ruff BLE001 rule

## Summary

24 instances of `except Exception` across the codebase. While sometimes intentional (graceful degradation), blind catches can:
- Hide bugs (catching exceptions you didn't expect)
- Make debugging harder (no type information)
- Violate "fail fast" principle

## Current Violations

### Category 1: CLI Error Boundaries (15 instances) - **ACCEPTABLE**

These are intentional - CLI commands should not crash with tracebacks:

```python
# commands/research/*.py - 12 instances
# commands/presenter.py - 1 instance
# All follow pattern:
try:
    result = store.operation(...)
except Exception as e:
    exit_with_result(ctx, handle_store_error("command name", e))
```

**Decision:** Keep as-is. CLI boundaries should catch all errors and present user-friendly output.

### Category 2: Optional Dependency Availability (4 instances) - **ACCEPTABLE**

```python
# core/pdf/converter.py - 4 instances
try:
    import marker  # or pdfplumber
    return True
except Exception:
    return False
```

**Decision:** Keep as-is. ImportError isn't enough - these libs can fail during import for various reasons.

### Category 3: Graceful Degradation (3 instances) - **REVIEW**

```python
# core/loop/runner.py:249 - LLM execution
except Exception as e:
    logger.error("LLM execution failed: %s", e)

# core/loop/service.py:156 - Skeleton generation
except Exception as e:
    return CLIOutput.err(...)

# core/search/enrichment.py:27 - Problem title lookup
except Exception:
    logger.debug("Failed to enrich...")
```

**Decision:** These could be more specific but are low risk.

### Category 4: Background Operations (2 instances) - **REVIEW**

```python
# core/loop/service.py:203 - Research attempt logging
except Exception as e:
    logger.warning("Failed to write research attempt record: %s", e)

# core/search/indexing_service.py:47 - Research indexing
except Exception:
    logger.warning("Research indexing skipped due to error", exc_info=True)
```

**Decision:** Acceptable - background/optional operations shouldn't crash main flow.

## Recommendation

**Do NOT enable BLE001 globally** - too many false positives for legitimate patterns.

Instead, review Category 3 cases individually:
1. `loop/runner.py:249` - Could catch `OSError | ValueError | subprocess.SubprocessError`
2. `loop/service.py:156` - Could catch `LeanRunnerError | OSError | ValueError`
3. `search/enrichment.py:27` - Could catch `KeyError | ProblemLoaderError`

## Acceptance Criteria

- [ ] Review 3 "graceful degradation" catches for specificity
- [ ] Document why each remaining `except Exception` is intentional
- [ ] Do NOT enable BLE001 in CI (too many valid use cases)

## Why Not Enable BLE001?

The rule is too strict for real-world code:
- CLI boundaries SHOULD catch all exceptions
- Optional dependency checks SHOULD catch all import failures
- Background operations SHOULD NOT crash main flow

A blanket `# noqa: BLE001` on every exception defeats the purpose.
