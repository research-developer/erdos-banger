# DEBT-072: CLI Flags Silently Ignored

**Status:** Open
**Priority:** P2 (Material quality gap)
**Found:** 2026-01-23
**Found By:** Codebase audit (CLI commands)

---

## Summary

Two CLI flags are accepted but silently ignored in certain modes, violating the principle of least surprise.

---

## Evidence

### 1. `erdos logs --summary` ignores `--status` (P2)

**File:** `src/erdos/commands/logs.py`

`--status` is defined as a CLI option, but it is not applied when `--summary` is used. The `summarize_logs()` helper does not accept (or pass) `status`, so `RunLogger.summary()` never receives a status filter.

```python
if summary:
    result = summarize_logs(
        run_logger,
        problem_id=problem_id,
        command=command,
        since=since,
        # status is not passed
    )
```

**Impact:** `erdos logs --summary --status success` returns an unfiltered summary.

---

### 2. `erdos convert --llm-service ...` is ignored unless `--use-llm` is set (P2)

**Files:**
- `src/erdos/commands/convert.py` (CLI accepts `--llm-service` even when `--use-llm` is false)
- `src/erdos/core/pdf/converter.py` (Marker config only applies `llm_service` inside `if use_llm:`)

In the core Marker integration, `llm_service` is only applied when `use_llm` is enabled:

```python
if use_llm:
    config.use_llm = True
    if llm_service:
        config.llm_service = llm_service.get_marker_class()
```

**Impact:** `erdos convert paper.pdf --llm-service claude` appears to select a service, but produces a non-LLM conversion with no error.

---

## Proposed Fix

### 1. `--status` with `--summary`

Either:
- Add `status` support to `summarize_logs()` and `RunLogger.summary(...)`, OR
- Enforce mutual exclusivity with a clear error:
  ```python
  if summary and status is not None:
      raise typer.BadParameter("--status cannot be used with --summary")
  ```

### 2. `--llm-service` requires `--use-llm`

Add validation in `src/erdos/commands/convert.py`:

```python
if llm_service is not None and not use_llm:
    raise typer.BadParameter("--llm-service requires --use-llm to be set")
```

---

## Acceptance Criteria

1. `erdos logs --summary --status ...` either filters correctly or fails with a clear usage error.
2. `erdos convert --llm-service ...` without `--use-llm` fails with a clear usage error.
3. `make ci` passes.
