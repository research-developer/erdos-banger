# DEBT-084: Unused OCP Patterns (register_summarizer, interrupt)

**Priority:** P3
**Status:** Open
**Found:** 2026-01-23
**Tool:** Vulture + code review

## Description

Two extensibility patterns were implemented following Open-Closed Principle (OCP) but are never actually used:

1. **`register_summarizer()`** - Registry pattern for custom log summarizers
2. **`BatchProcessor.interrupt()`** - Interrupt method for batch operations

These are YAGNI (You Ain't Gonna Need It) violations - infrastructure built for hypothetical future requirements that never materialized.

## Evidence

### 1. `register_summarizer` function

**Location:** `src/erdos/core/run_logger_summaries.py:103`

```python
def register_summarizer(command: str, summarizer: ResultSummarizer) -> None:
    """Register a custom summarizer for a command.

    This allows extending the summary system without modifying existing code (OCP).
    """
    _SUMMARIZERS[command] = summarizer
```

**Usage search:**
```bash
grep -r "register_summarizer" src/erdos/
# Only returns the definition in run_logger_summaries.py
```

**Status:** Never called anywhere. The `_SUMMARIZERS` registry only contains the built-in summarizers added directly to the dict literal.

### 2. `BatchProcessor.interrupt()` method

**Location:** `src/erdos/core/batch/runner.py:289-291`

```python
def interrupt(self) -> None:
    """Request graceful interruption of batch processing."""
    self._interrupted = True
```

**Usage search:**
```bash
grep -r "interrupt" src/erdos/core/batch/
# Returns:
# - self._interrupted = False (init)
# - if self._interrupted: (check)
# - def interrupt(self): (definition)
# - self._interrupted = True (implementation)
```

**Status:** The `interrupt()` method is never called from outside the class. The interrupt flag exists but there's no mechanism to trigger it (e.g., no signal handler, no CLI flag, no API endpoint).

## Root Cause

These patterns were likely added during architectural design as "good practices" but the actual use cases never materialized:

1. Custom summarizers are not needed because all commands use built-in summarization
2. Batch interruption was designed but never exposed to users

## Recommendation

**Option A (Recommended): Remove both patterns**
- Delete `register_summarizer()` function
- Remove `interrupt()` method and `_interrupted` flag from `BatchProcessor`
- If needed in the future, re-add with actual use cases

**Option B: Document as future hooks**
- Add explicit "TODO: wire up when X is implemented" comments
- Create placeholder tickets for when these would be useful

## Acceptance Criteria

- [ ] `register_summarizer` function removed
- [ ] `BatchProcessor.interrupt()` method and `_interrupted` flag removed
- [ ] No Vulture warnings for these items
- [ ] All tests pass
- [ ] Archive this debt deck

## Related

- DEBT-081: Incomplete features - tested but never wired in
- YAGNI principle: Don't build what you don't need yet
