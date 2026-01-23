# DEBT-082: Unused Constants in constants.py

**Priority:** P3
**Status:** Open
**Found:** 2026-01-23
**Tool:** Vulture (dead code analysis)

## Description

Eight constants are defined in `src/erdos/core/constants.py` but never imported or used anywhere in the codebase. These represent either:
1. Dead code from removed features
2. Constants intended for future use but never wired in
3. Copy-paste artifacts from initial scaffolding

## Evidence

Vulture output (60% confidence):
```
src/erdos/core/constants.py:8: unused variable 'MESSAGE_TRUNCATION' (60% confidence)
src/erdos/core/constants.py:11: unused variable 'TITLE_TRUNCATION' (60% confidence)
src/erdos/core/constants.py:14: unused variable 'TEXT_PREVIEW_LENGTH' (60% confidence)
src/erdos/core/constants.py:25: unused variable 'LEAN_COMPILE_TIMEOUT' (60% confidence)
src/erdos/core/constants.py:28: unused variable 'LAKE_UPDATE_TIMEOUT' (60% confidence)
src/erdos/core/constants.py:46: unused variable 'DEFAULT_SEARCH_LIMIT' (60% confidence)
src/erdos/core/constants.py:49: unused variable 'DEFAULT_RAG_LIMIT' (60% confidence)
src/erdos/core/constants.py:52: unused variable 'MAX_QUERY_TERMS' (60% confidence)
```

Verification via grep shows these constants are only defined, never imported:
```bash
grep -r "MESSAGE_TRUNCATION\|TITLE_TRUNCATION\|TEXT_PREVIEW_LENGTH" src/erdos/
# Only returns constants.py definitions

grep -r "DEFAULT_SEARCH_LIMIT\|DEFAULT_RAG_LIMIT\|MAX_QUERY_TERMS" src/erdos/
# Only returns constants.py definitions

grep -r "LEAN_COMPILE_TIMEOUT\|LAKE_UPDATE_TIMEOUT" src/erdos/
# Only returns constants.py definitions
```

## Constants

| Constant | Value | Intended Purpose | Status |
|----------|-------|------------------|--------|
| `MESSAGE_TRUNCATION` | 500 | Error message max length | Unused |
| `TITLE_TRUNCATION` | 50 | Title display max length | Unused |
| `TEXT_PREVIEW_LENGTH` | 100 | Short text previews | Unused |
| `LEAN_COMPILE_TIMEOUT` | 120 | Lean compile timeout (s) | Unused |
| `LAKE_UPDATE_TIMEOUT` | 600 | Lake update timeout (s) | Unused |
| `DEFAULT_SEARCH_LIMIT` | 10 | Default search results | Unused |
| `DEFAULT_RAG_LIMIT` | 5 | Default RAG chunks | Unused |
| `MAX_QUERY_TERMS` | 25 | Query term limit | Unused |

## Root Cause

Constants were defined speculatively or during initial design but never actually used when implementing features. The features hardcode their own values or use different defaults.

## Recommendation

**Remove all unused constants.** This is a greenfield project with no backwards compatibility requirements. If any constant is needed later, it can be re-added with proper usage.

## Acceptance Criteria

- [ ] Remove all 8 unused constants from `constants.py`
- [ ] Run `vulture src/erdos/ --min-confidence 60` - no constants flagged
- [ ] All tests pass
- [ ] Archive this debt deck

## Related

- DEBT-073: Magic numbers and hardcoded values (fixed)
- Pattern: Similar to BUG-022 where features were partially implemented
