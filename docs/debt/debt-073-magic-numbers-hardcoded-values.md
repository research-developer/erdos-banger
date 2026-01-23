# DEBT-073: Magic Numbers and Hardcoded Values

**Status:** Open
**Priority:** P3 (Minor - clean up when touching nearby code)
**Found:** 2026-01-23
**Found By:** Codebase audit (magic numbers)

---

## Summary

Some hardcoded values could be centralized for better maintainability. These are style/DRY issues, not correctness bugs.

---

## Verified Issues

### P3: Duplicated `DEFAULT_HTTP_TIMEOUT`

**Files:**
- `src/erdos/core/constants.py` - `DEFAULT_HTTP_TIMEOUT = 30.0`
- `src/erdos/core/config.py` - `DEFAULT_HTTP_TIMEOUT = 30.0`

**Impact:** DRY violation. Timeout defaults can drift.

---

### P3: Hardcoded Lean Version `v4.12.0`

**File:** `src/erdos/core/lean_runner.py`

The Lean toolchain version appears in more than one place (e.g. `lean-toolchain` contents and mathlib tag URL).

**Impact:** Version updates require changing multiple locations.

---

## Proposed Fix

1. Remove `DEFAULT_HTTP_TIMEOUT` from `src/erdos/core/config.py` and import it from `src/erdos/core/constants.py`.
2. (Optional) Introduce a single Lean version constant (e.g. `LEAN_TOOLCHAIN_VERSION`) in `src/erdos/core/constants.py` and use it from `lean_runner.py`.

---

## Acceptance Criteria

1. No duplicate `DEFAULT_HTTP_TIMEOUT` definitions remain.
2. `make ci` passes.
