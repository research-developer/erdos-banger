# DEBT-066: Test Directory Structure Should Mirror src/ Bounded Contexts

**Status:** Open
**Priority:** P3
**Found:** 2026-01-22
**Found By:** Clean Code audit (package organization review)

---

## Summary

The `tests/unit/` directory is a flat dumping ground with 50+ test files, while `src/erdos/core/` uses well-organized bounded-context subpackages. This violates the **Common Closure Principle** (CCP) - things that change together should be packaged together.

When you modify `src/erdos/core/search/service.py`, you should find its tests at `tests/unit/search/test_service.py`, not hunt through a flat list of 50+ files.

---

## Evidence

**src/ structure (organized):**
```
src/erdos/core/
├── ask/           # 4 modules
├── batch/         # 4 modules
├── search/        # 8 modules
├── loop/          # 6 modules
├── ingest/        # 5 modules
├── providers/     # 4 modules
└── ...
```

**tests/unit/ structure (flat):**
```
tests/unit/
├── test_ask_command_helpers.py
├── test_ask_helpers.py
├── test_ask_llm.py
├── test_ask_prompt.py
├── test_ask_retrieval.py
├── test_search_command_helpers.py
├── test_search_index.py
├── test_search_index_builder.py
├── test_search_index_embeddings.py
├── test_loop.py
├── test_loop_config.py
├── test_loop_verifier.py
├── ... (50+ files total)
```

---

## Recommended Fix

Reorganize `tests/unit/` to mirror `src/erdos/core/` bounded contexts:

```
tests/unit/
├── ask/
│   ├── __init__.py
│   ├── test_prompt.py
│   ├── test_retrieval.py
│   ├── test_llm.py
│   └── test_service.py
├── search/
│   ├── __init__.py
│   ├── test_service.py
│   ├── test_index.py
│   ├── test_builder.py
│   └── test_embeddings.py
├── loop/
│   ├── __init__.py
│   ├── test_runner.py
│   ├── test_config.py
│   └── test_verifier.py
├── ingest/
│   └── ...
├── providers/
│   └── ...
├── commands/
│   └── ...
└── conftest.py
```

**Steps:**
1. Create subdirectories matching `src/erdos/core/` bounded contexts
2. Move existing test files into appropriate subdirectories
3. Rename files to drop redundant prefixes (e.g., `test_ask_prompt.py` → `ask/test_prompt.py`)
4. Add `__init__.py` files to new directories
5. Update any imports in conftest.py if needed
6. Verify `make ci` passes

---

## Acceptance Criteria

1. [ ] `tests/unit/` has subdirectories mirroring `src/erdos/core/` bounded contexts
2. [ ] Each bounded context's tests are co-located in their subdirectory
3. [ ] No test files remain in the flat `tests/unit/` root (except `conftest.py`)
4. [ ] All tests still pass (`make ci`)
5. [ ] Test discovery still works correctly

---

## Non-Goals

- Changing test logic or coverage
- Reorganizing `tests/integration/` or `tests/e2e/` (separate debt if needed)
- Adding new tests

---

## Notes

This is organizational debt only - does not affect correctness. Prioritize after functional debt (DEBT-063 through DEBT-065) is resolved.
