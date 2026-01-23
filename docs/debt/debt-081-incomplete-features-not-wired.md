# DEBT-081: Incomplete Features — Tested but Never Wired In

**Priority:** P2 (Material quality gap; should be scheduled soon)

**Status:** Open

## Problem

Several features are partially implemented: the code exists and is tested, but it's never used in production. This creates:
1. Maintenance burden (code that can bitrot)
2. User confusion (tests suggest features exist that don't)
3. Spec drift (specs claim features that aren't exposed)

## Evidence

### 1. Citation Graph Methods — `OpenAlexClient.get_citations()` / `get_references()`

**Location:** `src/erdos/core/clients/openalex.py:451-485`

**What exists:**
```python
def get_citations(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
    """Get works that cite this work."""
    # Fully implemented, fetches from OpenAlex API

def get_references(self, work_id: str, *, limit: int = 25) -> list[ReferenceRecord]:
    """Get works cited by this work."""
    # Fully implemented, fetches from OpenAlex API
```

**Tests:** ✅ `tests/unit/clients/test_openalex.py:447-480`, `tests/integration/test_openalex_integration.py:75-85`

**Spec:** SPEC-020 Section 8 mentions `--enrich` flag for "additional metadata (citations, concepts)"

**What's missing:**
- No `--enrich` flag in `erdos ingest`
- No CLI command to query citation graph
- These methods are **never called** in production code

**Potential use cases:**
- "Find papers that cite this work" for literature discovery
- "Find papers this work cites" for background reading
- Recursive citation graph building for research mapping

---

### 2. `ReferenceRecord.best_url` Property

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

**Tests:** ✅ `tests/unit/models/test_base.py:77-87`

**What's missing:**
- Never used in any output formatting
- `erdos refs` and `erdos show` don't display URLs
- Could be useful for "click to read paper" links

---

### 3. `ProblemLoader.clear_cache()` Method

**Location:** `src/erdos/core/problem_loader.py:439`

**What exists:**
```python
def clear_cache(self) -> None:
    """Clear the problem cache, forcing reload on next access."""
    self._problems = None
```

**Tests:** ✅ `tests/unit/core/test_problem_loader.py:49-52`

**What's missing:**
- No CLI command to clear cache
- No programmatic callers
- Could be useful for `erdos refresh` or `--no-cache` flag

---

### 4. `RateLimiter.reset()` and `.last_call_time`

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

**Tests:** ❓ Not verified

**What's missing:**
- Never called in production
- Could be useful for testing or rate limit diagnostics

---

### 5. `is_retryable_error()` Function

**Location:** `src/erdos/core/retry.py:36`

**What exists:**
```python
def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (network timeout, connection error, etc.)."""
    # Implemented
```

**Tests:** ❓ May be tested

**What's missing:**
- Not used in the actual retry logic
- `fetch_with_retry()` has inline logic instead

---

### 6. `register_summarizer()` Function

**Location:** `src/erdos/core/run_logger_summaries.py:103`

**What exists:**
```python
def register_summarizer(
    command: str,
    summarizer: Callable[[list[RunLogEntry]], RunLogSummary],
) -> None:
    """Register a custom summarizer for a command."""
    _SUMMARIZER_REGISTRY[command] = summarizer
```

**Tests:** ❓ May be tested

**What's missing:**
- Never called — summarizers are registered inline instead
- OCP (Open/Closed Principle) violation: system should use this registry

---

## Related Issues

- **BUG-022:** `erdos ingest --pdf` flags silently ignored (same pattern — flags parsed but not wired)
- **DEBT-079:** literature_paths.py dead code (superseded by BUG-022)

## Proposed Fix

### Phase 1: Decide keep vs. remove for each

| Feature | Recommendation | Rationale |
|---------|---------------|-----------|
| Citation graph methods | **KEEP** — wire into CLI | Valuable for literature discovery |
| `best_url` property | **KEEP** — use in output | Improves UX for `erdos refs` |
| `clear_cache()` | **KEEP** — add `--no-cache` flag | Useful for development |
| `RateLimiter.reset()` | **REMOVE** or document as internal | Low value |
| `is_retryable_error()` | **REMOVE** or use in retry.py | Currently duplicated logic |
| `register_summarizer()` | **KEEP** — use in run_logger | OCP pattern already designed |

### Phase 2: Wire in or remove

For features marked KEEP:
1. Add CLI flags or commands to expose them
2. Document in `--help` and specs
3. Add integration tests

For features marked REMOVE:
1. Delete the code
2. Delete the tests
3. Update any specs that reference them

## Acceptance Criteria

- [ ] Each feature either wired in or removed
- [ ] No tested-but-unused code remains
- [ ] Specs updated to reflect actual implementation
- [ ] `make ci` passes

## Impact

- **Risk:** Medium (touches multiple modules)
- **Effort:** 4-6 hours across multiple files
- **Benefit:** Cleaner codebase, accurate specs, reduced maintenance burden

## References

- SPEC-020: `docs/_archive/specs/spec-020-openalex-integration.md` (Section 8: `--enrich`)
- BUG-022: `docs/bugs/bug-022-ingest-pdf-flags-silently-ignored.md`
- Detection: Vulture + manual trace
