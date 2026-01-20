# Technical Debt 026: Long Functions Remain (≥ 80 LOC)

**Date:** 2026-01-20
**Status:** Open
**Priority:** P2 (Maintainability / future refactors)
**Impact:** Harder reviews, higher bug risk during future changes, reduced testability

## Summary

The codebase has been substantially refactored toward smaller units, but there are still several functions ≥ 80 lines. These are mostly “do-everything” routines (parsing, ingestion orchestration, CLI command bodies) that will be hard to extend safely as v1.2+ adds more behavior.

This is not a correctness bug today (CI is green), but it is a predictable source of regressions when these areas are modified.

## Evidence (current ≥ 80 LOC functions)

Computed via AST (function `end_lineno - lineno + 1`):

- `src/erdos/core/lean_runner.py:162` — `LeanRunner.check` (~98 lines)
- `src/erdos/core/ingest/fetch.py:134` — `fetch_reference_entry` (~96 lines)
- `src/erdos/core/ingest/service.py:234` — `ingest_problem_references` (~92 lines)
- `src/erdos/commands/list_cmd.py:116` — `list_` (~91 lines; includes many Typer options)
- `src/erdos/commands/search.py:285` — `search` (~90 lines; includes Typer options + orchestration)
- `src/erdos/core/ingest/fetch.py:232` — `process_single_reference` (~88 lines)
- `src/erdos/core/problem_loader.py:139` — `_parse_problem` (~83 lines)

## Why This Matters (Clean Code)

- Large functions accumulate branching and mixed responsibilities (parsing + validation + orchestration + formatting).
- They reduce the effectiveness of unit tests (too many paths per function).
- They increase “edit blast radius” (small changes require re-reading large blocks).

## Proposed Resolution (high-level)

Prefer extracting helpers around distinct responsibilities:

- `LeanRunner.check`: split into “build command”, “run subprocess”, “parse output/errors”, “construct LeanCheckResult”.
- `fetch_reference_entry` / `process_single_reference`: split by source (Crossref vs arXiv), plus small pure transforms.
- `_parse_problem`: split per field group (id/status/title/text/refs) with localized validation and clear errors.
- Command callbacks (`list_`, `search`): keep Typer option definitions, but extract orchestration into small “core logic” helpers.

## Acceptance Criteria

- Each core function listed above is reduced below 80 LOC, or explicitly justified with an inline “linear parsing” rationale.
- New helper functions are pure where possible and have unit tests.
- `make ci` remains green.
