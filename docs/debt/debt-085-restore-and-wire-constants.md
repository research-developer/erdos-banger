# DEBT-085: Restore and Wire Removed Constants (DEBT-082 Regression)

**Priority:** P2
**Status:** Open
**Found:** 2026-01-23
**Caused By:** DEBT-082 fix (commit 117d510)

## Summary

DEBT-082 was incorrectly resolved by REMOVING constants instead of WIRING THEM IN. This is the exact BUG-022 pattern we identified before: "dead code" that was actually incomplete wiring.

Five constants were removed that should have been used to replace hardcoded magic numbers throughout the codebase. This violates DRY and makes configuration changes error-prone.

## Evidence

### Hardcoded Values That Should Use Constants

| Constant (Removed) | Hardcoded Value | Files Affected |
|--------------------|-----------------|----------------|
| `DEFAULT_SEARCH_LIMIT = 10` | `limit: int = 10` | ports.py, facade.py, bm25.py, fts_service.py, basic_service.py, embeddings_store.py, hybrid.py, mcp/server.py (20 places) |
| `DEFAULT_RAG_LIMIT = 5` | `limit: int = 5` | ask/service.py, loop/config.py, commands/ask.py, mcp/server.py |
| `LEAN_COMPILE_TIMEOUT = 120` | `timeout: int = 120` | lean/runner.py, loop/config.py, commands/loop.py |
| `LAKE_UPDATE_TIMEOUT = 600` | `timeout=600` | lean/runner.py, lean/aristotle.py, commands/lean/prove_cmd.py |
| `MAX_QUERY_TERMS = 25` | `terms[:25]` | ask/retrieval.py:63 |

### Verification

```bash
# 20 hardcoded limit=10 instances
grep -rn "limit.*=.*10\|limit: int = 10" src/erdos/ | wc -l
# 4 hardcoded timeout=120 instances
grep -rn "timeout.*=.*120" src/erdos/ | wc -l
# 4 hardcoded timeout=600 instances
grep -rn "timeout.*=.*600" src/erdos/ | wc -l
# 1 hardcoded terms[:25]
grep -rn "terms\[:25\]" src/erdos/
```

### Constants Correctly Removed (Legitimately Unused)

These three were correctly removed as they had no corresponding hardcoded values:
- `MESSAGE_TRUNCATION = 500` - No truncation using this value exists
- `TITLE_TRUNCATION = 50` - No truncation using this value exists
- `TEXT_PREVIEW_LENGTH = 100` - No truncation using this value exists

## Root Cause

The DEBT-082 fix treated all "unused" constants as dead code without checking if hardcoded magic numbers existed that SHOULD be using them. This is the BUG-022 anti-pattern: removing scaffolding instead of completing the wiring.

## Correct Fix

1. **Restore 5 constants** to `src/erdos/core/constants.py`:
   ```python
   DEFAULT_SEARCH_LIMIT = 10
   """Default number of search results to return."""

   DEFAULT_RAG_LIMIT = 5
   """Default number of RAG context chunks to retrieve."""

   LEAN_COMPILE_TIMEOUT = 120
   """Timeout for Lean compilation operations."""

   LAKE_UPDATE_TIMEOUT = 600
   """Timeout for lake update operations."""

   MAX_QUERY_TERMS = 25
   """Maximum number of query terms to extract from user questions."""
   ```

2. **Replace all hardcoded values** with imports from constants:
   - Update `limit: int = 10` → `limit: int = DEFAULT_SEARCH_LIMIT`
   - Update `limit: int = 5` (RAG) → `limit: int = DEFAULT_RAG_LIMIT`
   - Update `timeout: int = 120` → `timeout: int = LEAN_COMPILE_TIMEOUT`
   - Update `timeout=600` → `timeout=LAKE_UPDATE_TIMEOUT`
   - Update `terms[:25]` → `terms[:MAX_QUERY_TERMS]`

3. **Update test_constants.py** to verify the restored constants

## Acceptance Criteria

- [ ] 5 constants restored to `constants.py`
- [ ] All 37+ hardcoded instances replaced with constant imports
- [ ] `grep -rn "limit: int = 10" src/erdos/` returns 0 results (except protocol definitions)
- [ ] `grep -rn "timeout: int = 120" src/erdos/` returns 0 results (except CLI defaults)
- [ ] `grep -rn "timeout=600" src/erdos/` returns 0 results (except CLI defaults)
- [ ] `make ci` passes
- [ ] Archive this debt deck

## Impact

**Medium** - DRY violation makes configuration changes risky. Changing search limit requires editing 20 files instead of 1.

## Related

- DEBT-082: Removed constants (incorrectly)
- BUG-022: PDF flags silently ignored (same pattern - incomplete wiring treated as dead code)
- DEBT-073: Magic numbers and hardcoded values (only addressed HTTP timeout duplication)
