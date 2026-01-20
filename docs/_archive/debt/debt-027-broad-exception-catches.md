# Technical Debt 027: Broad `except Exception` Catches (Masking Risk)

**Date:** 2026-01-20
**Status:** Fixed
**Fixed In:** e657d7c
**Priority:** P3 (Quality / diagnosability)
**Impact:** Programmer errors can be misclassified as user errors; stack traces can be lost unless reproduced under a debugger

## Summary

The codebase uses broad `except Exception` in multiple places. Some are appropriate (e.g., transaction rollback wrappers or top-level CLI boundaries), but others sit inside core logic where they risk hiding real defects and making failures harder to debug.

This is not a failing-test issue today, but it increases maintenance risk.

## Evidence (non-exhaustive)

### CLI boundaries (usually acceptable, but should preserve context)

- `src/erdos/commands/list_cmd.py:106`
- `src/erdos/commands/show.py:77`
- `src/erdos/commands/refs.py:66`
- `src/erdos/commands/search.py:211`
- `src/erdos/commands/lean.py:87`, `src/erdos/commands/lean.py:119`

### Core logic (higher masking risk)

- `src/erdos/core/ingest/service.py:33`
- `src/erdos/core/ingest/fetch.py:308`
- `src/erdos/core/formalizer.py:67`
- `src/erdos/core/ask/llm.py:101`
- `src/erdos/core/ask/service.py:37`, `src/erdos/core/ask/service.py:58`

### Transaction boundary (appropriate pattern)

- `src/erdos/core/search_index.py:85` (rollback then re-raise)

## Why This Matters (Clean Code)

Broad catches conflate:

- expected operational errors (network timeouts, missing files, invalid user input), and
- unexpected programming errors (TypeError, AttributeError, invariant violations).

If everything becomes “Error: {str(e)}”, debugging becomes slower and more fragile.

## Proposed Resolution (high-level)

- Prefer catching specific, named exception types in core services (e.g., `ProblemLoaderError`, `SearchIndexError`, `IngestError`, `AskError`).
- Keep broad catches only at:
  - CLI entrypoints (to ensure `--json` contract always returns JSON), and
  - rollback wrappers that re-raise.
- When broad catches are kept, ensure the traceback is preserved via logging (e.g., `logger.exception(...)`) when `--log-level=DEBUG`.

## Acceptance Criteria

- Core service layers no longer use `except Exception` except where re-raising after cleanup.
- CLI boundary code returns friendly errors but retains enough debug signal (traceback/logging) for diagnosis.
- `make ci` remains green.
