# DEBT-091: Blind Exception Catches (BLE001)

**Priority:** P3
**Status:** Fixed (scope-limited)
**Found:** 2026-01-23
**Fixed:** 2026-01-24
**Fix Commit:** 22f14f6

## Summary

An ad-hoc audit identified a number of `except Exception` catches. Many are intentional (CLI boundaries, optional dependency checks, best-effort background operations). The high-signal places to tighten were a small set of core boundaries.

## Resolution

Tightened exception boundaries where we can be specific without harming UX:

- Loop iteration LLM execution now catches only execution-related exceptions:
  - `OSError | ValueError | subprocess.SubprocessError`
- Loop skeleton generation catches the domain error (`FormalizerError`) instead of `Exception`.
- Search indexing fails fast on index-level errors by raising `SearchIndexError` rather than swallowing unexpected exceptions.

Intentionally retained broad exception catches at:
- CLI command boundaries (user-friendly error output)
- optional dependency probing for PDF converters
- best-effort enrichment/background tasks

## Verification

- `make ci`

## Acceptance Criteria

- [x] High-signal core catches narrowed
- [x] Broad catches retained only at deliberate boundaries
- [x] `make ci` passes
