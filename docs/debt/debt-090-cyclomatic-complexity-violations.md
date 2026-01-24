# DEBT-090: Cyclomatic Complexity Violations (C901)

**Status:** Identified
**Created:** 2026-01-23
**Priority:** P2
**Found By:** Ruff C901 rule (cyclomatic complexity > 10)

## Summary

4 functions exceed Ruff's cyclomatic complexity threshold of 10. High complexity correlates with:
- Harder to test (more paths to cover)
- Harder to understand (more branches)
- Higher bug density

## Current Violations

```
C901 `openalex_to_reference` is too complex (11 > 10)
   --> src/erdos/core/clients/openalex.py:229:5

C901 `validate_patch` is too complex (11 > 10)
   --> src/erdos/core/loop/patch_validator.py:249:5

C901 `_run_single_iteration` is too complex (13 > 10)
   --> src/erdos/core/loop/runner.py:191:5

C901 `query` is too complex (11 > 10)
   --> src/erdos/core/run_logger.py:305:9
```

## Analysis

### 1. `openalex_to_reference` (complexity: 11)
**Location:** `core/clients/openalex.py:229`
**Issue:** Data transformation with many optional fields
**Recommendation:** Extract field extractors or use a mapping pattern

### 2. `validate_patch` (complexity: 11)
**Location:** `core/loop/patch_validator.py:249`
**Status:** Already documented in DEBT-088 as acceptable validation pipeline
**Decision:** Won't fix - guard clause pattern is appropriate here

### 3. `_run_single_iteration` (complexity: 13)
**Location:** `core/loop/runner.py:191`
**Status:** Already documented in DEBT-086 for refactoring
**Decision:** Will be addressed by DEBT-086

### 4. `query` (complexity: 11)
**Location:** `core/run_logger.py:305`
**Issue:** Query builder with many optional filters
**Recommendation:** Extract filter builders or use query object pattern

## New Work Required

Only 2 functions need new work:
1. `openalex_to_reference` - Extract field mapping helpers
2. `run_logger.query` - Extract filter builders

## Acceptance Criteria

- [ ] Reduce `openalex_to_reference` complexity to ≤10
- [ ] Reduce `run_logger.query` complexity to ≤10
- [ ] Add C901 to Ruff config to catch future violations
- [ ] Existing DEBT-086/088 cover the other 2 violations

## How to Enable C901 in CI

Add to `pyproject.toml`:
```toml
[tool.ruff.lint]
select = [
    # ... existing rules ...
    "C90",    # mccabe complexity
]

[tool.ruff.lint.mccabe]
max-complexity = 10
```
