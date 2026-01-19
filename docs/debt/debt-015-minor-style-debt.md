# Technical Debt 015: Minor Style Debt (Post v1.1)

**Date:** 2026-01-19
**Status:** Resolved
**Priority:** P4 (Low - cosmetic/style)
**Impact:** None functional, style consistency only

## Items

### 1. `code=1` vs `ExitCode.ERROR` Inconsistency

**Status:** Fixed (commit `9df84ca`)

**Files affected:**
- `src/erdos/commands/lean.py` (6 occurrences)
- `src/erdos/commands/refs.py` (2 occurrences)
- `src/erdos/commands/search.py` (4 occurrences)
- `src/erdos/commands/show.py` (2 occurrences)
- `src/erdos/commands/list_cmd.py` (2 occurrences)

**Note:** `src/erdos/core/ask.py` was normalized to `ExitCode.ERROR` in commit `8acca96`.

**Issue:** Some error returns use `code=1` directly instead of `code=ExitCode.ERROR`.

**Impact:** None - `ExitCode.ERROR = 1`, so functionally equivalent.

**Fix:** Replaced all 16 occurrences with `code=ExitCode.ERROR` and added imports.

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

### 4. Lean Formalize Template Missing Newline

**File:** `src/erdos/templates/lean_skeleton.j2`
**Status:** Fixed (commit `27c0a16`)

**Issue:** The generated Lean file has "Prize: $100Tags:" with no newline between prize and tags.

**Example output:**
```lean
Status: proved
Prize: $100Tags: number theory, primes, arithmetic progressions
```

**Expected:**
```lean
Status: proved
Prize: $100
Tags: number theory, primes, arithmetic progressions
```

**Impact:** Low - cosmetic issue in generated comment block.

**Fix:** Add newline before `Tags:` in the Jinja2 template.

## Resolution

- Item 1: Fixed - all 16 occurrences normalized to `ExitCode.ERROR`
- Item 2: No action needed (valid pattern)
- Item 3: No action needed (intentional UX)
- Item 4: Fixed in commit `27c0a16`

**All actionable items resolved.**

## References

- ExitCode enum: `src/erdos/core/exit_codes.py`
- Clean Code style guide: Rob C. Martin
