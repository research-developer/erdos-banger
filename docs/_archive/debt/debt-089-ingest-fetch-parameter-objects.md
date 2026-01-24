# DEBT-089: Ingest/Fetch Long Parameter Lists

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** 22f14f6

## Summary

Several functions in `src/erdos/core/ingest/fetch.py` had large parameter lists (8–14 keyword-only arguments). This increased cognitive load, made signatures brittle, and cluttered call sites and tests.

## Resolution

- Introduced config “parameter objects” in `src/erdos/core/ingest/config.py`:
  - `FetchConfig`
  - `PDFConfig`
  - `IngestConfig`
  - `MetadataSource`
- Refactored ingest fetch functions to accept an `IngestConfig` instead of passing 10+ parameters through the stack.
- Updated service orchestration and tests to construct and pass `IngestConfig`.

## Verification

- `make ci`

## Acceptance Criteria

- [x] Config objects created and used across ingest/fetch
- [x] Function signatures reduced to manageable size
- [x] Call sites updated (service + tests)
- [x] `make ci` passes
