# Technical Debt 015: Minor Style Debt (Post v1.1)

**Date:** 2026-01-19
**Status:** Open
**Priority:** P4 (Low - cosmetic/style)
**Impact:** None functional, style consistency only

## Items

### 1. `code=1` vs `ExitCode.ERROR` Inconsistency

**Files affected:**
- `src/erdos/commands/lean.py` (6 occurrences)
- `src/erdos/commands/refs.py` (2 occurrences)
- `src/erdos/commands/search.py` (4 occurrences)
- `src/erdos/commands/show.py` (2 occurrences)
- `src/erdos/commands/list_cmd.py` (2 occurrences)

**Note:** `src/erdos/core/ask.py` was normalized to `ExitCode.ERROR` in commit `8acca96`.

**Issue:** Some error returns use `code=1` directly instead of `code=ExitCode.ERROR`.

**Impact:** None - `ExitCode.ERROR = 1`, so functionally equivalent.

**Fix:** Replace `code=1` with `code=ExitCode.ERROR` for consistency.

### 2. Broad `except Exception` at CLI Boundary

**Files affected:**
- `src/erdos/commands/lean.py`
- `src/erdos/commands/refs.py`
- `src/erdos/commands/search.py`
- `src/erdos/commands/show.py`
- `src/erdos/commands/list_cmd.py`
- `src/erdos/core/ask.py`
- `src/erdos/core/formalizer.py`
- `src/erdos/core/search_index.py`

**Issue:** Broad exception catching at CLI command boundaries.

**Impact:** None - this is a valid defensive pattern for CLI apps to prevent crashes.

**Decision:** Keep as-is. CLI boundary layers should catch broadly to provide user-friendly errors.

### 3. Template TODOs in `lean_skeleton.j2`

**File:** `src/erdos/templates/lean_skeleton.j2:28, 42`

**Issue:** Contains `## TODO` and `-- TODO: Refine this formal statement` comments.

**Impact:** None - these are intentional placeholders for users to fill in when formalizing problems.

**Decision:** Keep as-is. These guide users, not developer action items.

## Resolution

- Item 1: Fix when touching affected files (opportunistic cleanup)
- Item 2: No action needed (valid pattern)
- Item 3: No action needed (intentional UX)

## References

- ExitCode enum: `src/erdos/core/exit_codes.py`
- Clean Code style guide: Rob C. Martin
