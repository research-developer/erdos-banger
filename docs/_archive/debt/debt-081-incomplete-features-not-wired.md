# DEBT-081: Incomplete Features — Tested but Never Wired In

**Priority:** P2 (Material quality gap; should be scheduled soon)

**Status:** Fixed
**Fixed:** 2026-01-23
**Commit:** 05a1161, 4614bd8

## Problem

This deck tracked two real issues:

1) **Spec drift:** a “Complete” spec claimed CLI flags that do not exist.
2) **Tested-but-unused logic:** `is_retryable_error()` was tested but unused in the production retry path.

Other findings (client methods or small helpers only used in tests) were validated as acceptable
internal APIs and do not require user-facing CLI wiring.

## Evidence

### 1. Spec-020 claimed CLI flags that were not implemented (fixed)

**Location:** `src/erdos/core/clients/openalex.py:451-485`

**What exists:**
```python
def get_citations(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
    """Get works that cite this work."""
    # Fully implemented, fetches from OpenAlex API

def get_references(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
    """Get related works via OpenAlex filter."""
    # Fully implemented, fetches from OpenAlex API
```

**Tests:**
- ✅ Unit: `tests/unit/clients/test_openalex.py` (covers both methods; asserts filter query param)
- ✅ Network: `tests/integration/test_openalex_integration.py` (covers `get_citations`; `requires_network`)

`docs/_archive/specs/spec-020-openalex-integration.md` previously claimed CLI flags that do not exist
(`--enrich`, `--external`). The spec was corrected to explicitly mark these as deferred.

**What's missing:**
- No CLI flag/command uses these citation graph methods today
- Specs should not claim CLI flags that are not implemented

**Potential use cases:**
- "Find papers that cite this work" for literature discovery
- "Find papers this work cites" for background reading
- Recursive citation graph building for research mapping

---

### 2. `ReferenceRecord.best_url` is an internal convenience (not a CLI feature)

**Location:** `src/erdos/core/models/reference.py:101-110`

**What exists:**
```python
@property
def best_url(self) -> str | None:
    """Return the best available URL for accessing this reference."""
    if self.oa_url:
        return self.oa_url
    if self.arxiv_id:
        return f"https://arxiv.org/abs/{self.arxiv_id}"
    if self.doi:
        return f"https://doi.org/{self.doi}"
    return None
```

**Tests:** ✅ `tests/unit/models/test_base.py` (covers URL priority)

`best_url` is a computed property on `ReferenceRecord` (ingested references), not the dataset
`ReferenceEntry` shown by `erdos refs`. No current CLI command prints a “best URL” for ingested
references, so treating this as user-facing functionality would require an explicit UX decision
and tests.

---

### 3. `ProblemLoader.clear_cache()` exists but is only used by tests

**Location:** `src/erdos/core/problem_loader.py:439`

**What exists:**
```python
def clear_cache(self) -> None:
    """Clear the problem cache, forcing reload on next access."""
    self._cache = None
```

**Tests:** ✅ `tests/unit/core/test_problem_loader.py` (covers cache invalidation)

**What's missing:**
- No non-test callers today.

This is likely intentional as an internal/testing helper. If we keep it, we should treat it as
internal API (docstring clarity) rather than an “incomplete user feature”.

---

### 4. `RateLimiter.reset()` / `.last_call_time` are internal helpers (tested)

**Location:** `src/erdos/core/rate_limiter.py:44,74`

**What exists:**
```python
@property
def last_call_time(self) -> float | None:
    """Get the timestamp of the last call."""
    return self._last_call_time

def reset(self) -> None:
    """Reset the rate limiter state."""
    self._last_call_time = None
```

**Tests:** ✅ `tests/unit/core/test_rate_limiter.py` (covers both)

**What's missing:**
- Not used by production code today (BatchRunner uses `sleep_if_needed()`).

---

### 5. `is_retryable_error()` tested-but-unused helper (fixed)

`is_retryable_error()` was removed, and its unit tests were removed. The production retry loop
(`fetch_with_retry`) remains the SSOT.

---

### 6. `register_summarizer()` is tested but not used by production wiring

**Location:** `src/erdos/core/run_logger_summaries.py:103`

**What exists:**
```python
def register_summarizer(
    command: str,
    summarizer: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Register a custom summarizer for a command."""
    SUMMARIZERS[command] = summarizer
```

**Tests:** ✅ `tests/unit/core/test_run_logger_summaries.py` (covers registering + end-to-end)

**What's missing:**
- Not called by production code today (only used in tests), but it is a valid extension hook.
- The OCP boundary is still satisfied because `run_logger` consumes the registry via `get_summarizer()`.

---

## Related Issues

- **BUG-022:** `erdos ingest --pdf` flags silently ignored (same pattern — flags parsed but not wired)
- **DEBT-079:** literature_paths.py dead code (superseded by BUG-022)

## Proposed Fix

No additional code changes are required. New CLI capabilities (citation graph, enrichment, etc.)
should be introduced via a dedicated spec and implemented end-to-end (CLI + core + tests) in a
single PR.

## Acceptance Criteria

- [x] Specs do not claim CLI flags/commands that are not implemented
- [x] No CLI flags are silently ignored (BUG-022 class)
- [x] Tested-but-unused helper logic removed
- [ ] `make ci` passes

## Impact

- **Risk:** Medium (touches multiple modules)
- **Effort:** 4-6 hours across multiple files
- **Benefit:** Cleaner codebase, accurate specs, reduced maintenance burden

## References

- SPEC-020: `docs/_archive/specs/spec-020-openalex-integration.md` (Section 8: `--enrich`)
- BUG-022: `docs/bugs/bug-022-ingest-pdf-flags-silently-ignored.md`
- Detection: Vulture + manual trace
