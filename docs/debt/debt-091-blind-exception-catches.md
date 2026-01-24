# DEBT-091: Blind Exception Catches (BLE001)

**Status:** Identified
**Created:** 2026-01-23
**Priority:** P3
**Found By:** Ad-hoc `ruff check --select BLE001` (BLE not enabled in CI)

## Summary

43 instances of `except Exception` across the codebase. While sometimes intentional (graceful degradation / user-facing error boundaries), blind catches can:
- Hide bugs (catching exceptions you didn't expect)
- Make debugging harder (no type information)
- Violate "fail fast" principle

## Current Violations

### Category 1: CLI Error Boundaries (`src/erdos/commands/**`, 26 instances) - **ACCEPTABLE**

These are intentional - CLI commands should not crash with tracebacks:

```python
# commands/** - 26 instances (research/, lean/, logs, show, list, refs, presenter)
# All follow pattern:
try:
    result = store.operation(...)
except Exception as e:
    exit_with_result(ctx, handle_store_error("command name", e))
```

**Decision:** Keep as-is. CLI boundaries should catch all errors and present user-friendly output.

### Category 2: Error Translation Boundaries (`src/erdos/core/**`, 8 instances) - **ACCEPTABLE**

These are used to convert unexpected exceptions into domain errors (or `CLIOutput`)
without a traceback for end users:

- `core/lean/formalizer.py` (wraps into `FormalizerError`)
- `core/loop/runner.py` (LLM execution boundary; logs and returns `LoopStatus.ERROR`)
- `core/loop/service.py` (skeleton generation + loop execution)
- `core/search/basic_service.py`, `core/search/fts_service.py` (return `CLIOutput.err(...)`)
- `core/ingest/fetch.py`, `core/batch/runner.py` (log + return structured failure)

**Decision:** Keep as-is unless a narrower exception set is clearly correct (see “Recommendation”).

### Category 3: Transaction/Rollback Boundary (1 instance) - **ACCEPTABLE**

```python
# core/search/db.py - rollback then re-raise
try:
    yield conn
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

**Decision:** Keep as-is. This is a standard pattern.

### Category 4: Optional Dependency Availability (4 instances) - **ACCEPTABLE**

```python
# core/pdf/converter.py - 4 instances
try:
    import marker  # or pdfplumber
    return True
except Exception:
    return False
```

**Decision:** Keep as-is. ImportError isn't enough - these libs can fail during import for various reasons.

### Category 5: Best-effort / Background Operations (4 instances) - **ACCEPTABLE**

- `core/search/index_builder.py` (per-problem indexing failures are logged and skipped)
- `core/search/indexing_service.py` (research indexing is best-effort)
- `core/loop/service.py:203` (attempt logging is best-effort)
- `core/search/enrichment.py` (result enrichment is best-effort)

```python
# core/search/enrichment.py:27 - result enrichment
except Exception:
    logger.debug("Failed to enrich...")
```

**Decision:** Acceptable - background/optional operations shouldn't crash main flow.

## Recommendation

**Do NOT enable BLE001 globally** - too many legitimate false positives for this codebase.

Note: BLE001 is not currently selected in `pyproject.toml`, so this does not fail CI today.

Instead, selectively tighten a few high-signal cases:
1. `core/loop/runner.py:249` - likely `OSError | ValueError | subprocess.SubprocessError`
2. `core/loop/service.py:156` - likely `FormalizerError | OSError | ValueError`
3. `core/search/index_builder.py:54` - consider catching `SearchIndexError` (or the index port’s concrete errors)

## Acceptance Criteria

- [ ] Review 3 core catches for specificity (above)
- [ ] Document why each remaining `except Exception` is intentional
- [ ] Do NOT enable BLE001 in CI (too many valid use cases)

## Why Not Enable BLE001?

The rule is too strict for real-world code:
- CLI boundaries SHOULD catch all exceptions
- Optional dependency checks SHOULD catch all import failures
- Background operations SHOULD NOT crash main flow

A blanket `# noqa: BLE001` on every exception defeats the purpose.
