# DEBT-081: Incomplete Features — Tested but Never Wired In

**Priority:** P2 (Material quality gap; should be scheduled soon)

**Status:** Open

## Problem

Several features are partially implemented: the code exists (often with tests), but it is either:
1) **Not reachable from the CLI**, despite being documented in specs, or
2) **Only reachable from tests**, with unclear intent as public API.

This creates:
1. Maintenance burden (code that can bitrot)
2. User confusion (tests suggest features exist that don't)
3. Spec drift (specs claim features that aren't exposed)

## Evidence

### 1. OpenAlex citation graph methods exist but are not surfaced via CLI/specs

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

**Spec drift evidence:** `docs/_archive/specs/spec-020-openalex-integration.md` claims CLI flags that do not exist:
- `erdos ingest --enrich`
- `erdos search --external`
- `erdos refs <id> --enrich`

**What's missing:**
- No CLI flag/command uses these citation graph methods today
- Specs should not claim CLI flags that are not implemented

**Potential use cases:**
- "Find papers that cite this work" for literature discovery
- "Find papers this work cites" for background reading
- Recursive citation graph building for research mapping

---

### 2. `ReferenceRecord.best_url` exists but is not used in user-facing output

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

**What's missing:**
- Not displayed by `erdos refs` (and therefore not easily discoverable from CLI output)

This is not a correctness bug, but it is a UX gap if the CLI intends to help users open papers.

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

### 5. `is_retryable_error()` is tested but unused by the retry loop

**Location:** `src/erdos/core/retry.py:36`

**What exists:**
```python
def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (network timeout, connection error, etc.)."""
    # Implemented
```

**Tests:** ✅ `tests/unit/core/test_retry.py` (covers this helper)

**What's missing:**
- The main retry loop (`fetch_with_retry`) does not use this helper, so we effectively test logic
  that is not part of the production path.

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

### Phase 1: Split real user-facing drift from internal helpers

**User-facing drift (should be addressed):**
- Spec-020 claims CLI flags that do not exist (`--enrich`, `--external`).
- BUG-022 is the same “flag exists but no effect” class of issue.

**Internal helpers (evaluate case-by-case):**
- `ProblemLoader.clear_cache()`, `RateLimiter.reset()`, `register_summarizer()`

These may be acceptable if treated as internal API and documented as such.

| Item | Recommendation | Rationale |
|------|----------------|-----------|
| Spec-020 CLI claims | **Fix docs** (or implement) | Specs must match reality |
| OpenAlex citation graph methods | **Defer or spec** | Valuable, but currently not a user feature |
| `best_url` property | **Optional UX enhancement** | Helpful for CLI output, not required |
| `clear_cache()` / `reset()` / `register_summarizer()` | **Keep (internal)** | Small, tested utilities; clarify intent |
| `is_retryable_error()` | **Either use or remove** | Avoid tested-but-unused logic |

### Phase 2: Wire in or remove

If we choose to expose new CLI capabilities (citation graph, `--enrich`, etc.), treat that as a
tracked spec and implement end-to-end (CLI + core + tests) in one PR.

If we choose to remove helpers (e.g. `is_retryable_error`), remove the helper *and* its tests, and
ensure the production retry loop retains correct behavior and coverage.

## Acceptance Criteria

- [ ] Specs do not claim CLI flags/commands that are not implemented
- [ ] No CLI flags are silently ignored (BUG-022 class)
- [ ] “Internal helper” APIs are clearly documented as internal/testing utilities
- [ ] `make ci` passes

## Impact

- **Risk:** Medium (touches multiple modules)
- **Effort:** 4-6 hours across multiple files
- **Benefit:** Cleaner codebase, accurate specs, reduced maintenance burden

## References

- SPEC-020: `docs/_archive/specs/spec-020-openalex-integration.md` (Section 8: `--enrich`)
- BUG-022: `docs/bugs/bug-022-ingest-pdf-flags-silently-ignored.md`
- Detection: Vulture + manual trace
