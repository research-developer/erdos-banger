# DEBT-067: Remove Private Helper Re-exports from Core Packages

**Status:** Open
**Priority:** P3
**Found:** 2026-01-23
**Found By:** Clean architecture audit (public API surface + test coupling)

---

## Summary

Some `erdos.core.*` packages currently re-export **private helper functions** (names starting with `_`) and/or define private alias symbols solely to support tests importing from the package root. This inflates the public API surface and makes refactors riskier in a greenfield codebase.

This debt is about **tightening the public surface** and making tests import from **canonical implementation modules**, not from convenience re-exports.

---

## Evidence

### `erdos.core.ask` exports private helpers

- `src/erdos/core/ask/__init__.py` exports private helpers and aliases:
  - `_ensure_index_ready`, `_load_problem`, `_build_response_data`
  - `_fallback_sources`, `_retrieve_sources`, `_execute_llm_if_enabled`

### `erdos.core.ingest` exports private helpers

- `src/erdos/core/ingest/__init__.py` exports private helpers and aliases:
  - `_download_and_extract_arxiv`, `_fetch_reference_entry`
  - `_process_all_references`, `_process_single_reference`

### Tests depend on those private re-exports

- `tests/unit/ask/test_helpers.py` imports private names from `erdos.core.ask`:
  - `_ensure_index_ready`, `_load_problem`, `_build_response_data`

---

## Why This Is Debt (Clean Code)

- **SRP:** package `__init__.py` mixes public API design with test-only aliasing.
- **OCP:** internal helpers become “semi-public” by accident; renames require broader coordination.
- **Clarity:** makes it harder to know which module is the SSOT for a helper.

---

## Proposed Fix

1. Update tests to import private helpers from their **implementation modules**:
   - `erdos.core.ask.service` for `_ensure_index_ready`, `_load_problem`, `_build_response_data`
   - `erdos.core.ingest.fetch` for fetch/process helpers (if they remain testable units)
2. Remove underscore-prefixed exports/aliases from package roots:
   - `src/erdos/core/ask/__init__.py`
   - `src/erdos/core/ingest/__init__.py`
3. Keep only stable public API in package roots:
   - `ask_question`, `build_prompt`, `perform_retrieval`, `execute_llm` (ask)
   - `execute_ingest`, `ingest_problem_references`, and public result dataclasses (ingest)
4. Add a regression guard test:
   - Fail if any `__all__` in `src/erdos/core/*/__init__.py` contains a name starting with `_`.

---

## Acceptance Criteria

1. No tests import private helpers from package roots:
   - `rg -n "from erdos\\.core\\.ask import _" tests` returns no matches
   - `rg -n "from erdos\\.core\\.ingest import _" tests` returns no matches
2. Package public APIs are clean:
   - `rg -n "\"_\"|_ensure_index_ready|_download_and_extract_arxiv" src/erdos/core/*/__init__.py` returns no matches
3. All quality gates pass:
   - `make ci`
