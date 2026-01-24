# DEBT-085: Restore and Wire Removed Constants (DEBT-082 Regression)

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** c5b5d9f, f70613a

## Summary

Commit `117d510` (DEBT-082) removed several “unused” constants from `src/erdos/core/constants.py`. Those constants were not truly dead: their values were duplicated as defaults and truncation lengths across core services, CLI adapters, and the MCP server.

This fix restores those constants and wires them into the relevant defaults, removing drift risk while keeping the values and behavior unchanged.

## Resolution

- Restored shared defaults/truncation constants to `src/erdos/core/constants.py` and ensured they are actually used:
  - `DEFAULT_SEARCH_LIMIT`
  - `DEFAULT_RAG_LIMIT`
  - `LEAN_COMPILE_TIMEOUT`
  - `LAKE_UPDATE_TIMEOUT` (used for `lake update`, not Aristotle)
  - `MAX_QUERY_TERMS`
  - `MESSAGE_TRUNCATION`
  - `TITLE_TRUNCATION`
  - `TEXT_PREVIEW_LENGTH`
- Replaced duplicated literals in:
  - Search defaults across ports + search services + CLI + MCP
  - RAG defaults across ask/loop + CLI + MCP
  - Lean timeouts in loop config/CLI + Lean runner
  - Aristotle module timeouts (AristotleConfig, run_aristotle_prove_from_file, prove command)
  - Query-term slicing in ask retrieval
  - UI truncation lengths in CLI output
- Updated unit tests covering the constants module.

## Acceptance Criteria

- [x] Restored constants are used by real call sites (no dead exports)
- [x] Search/RAG defaults and Lean timeouts are single-sourced
- [x] `make ci` passes
