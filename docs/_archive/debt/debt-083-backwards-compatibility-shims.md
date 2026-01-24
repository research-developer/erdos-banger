# DEBT-083: Remove Internal Compatibility Shims + Misleading Wording

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-23
**Fix Commit:** 117d510

## Summary

We had a handful of “compatibility” artifacts that increased ambiguity without providing real value:

- A deprecated `build_metadata_provider()` helper in `src/erdos/core/context.py` used only by tests.
- `SearchIndex._connect()` which exposed raw DB access as a test-only escape hatch.
- Package/module comments describing the canonical public API as “backward compatibility”.

## Resolution

- Deleted `build_metadata_provider()` and updated tests to use `build_provider_from_source()` (re-exported via `erdos.core.ingest`).
- Removed `SearchIndex._connect()` and updated tests to connect via `sqlite3.connect(index.db_path)`.
- Removed “backward compatibility” wording across `src/erdos/` and clarified intent as *public API re-exports* (stable package boundaries).

## Acceptance Criteria

- [x] Deprecated shims removed
- [x] Tests use canonical public surfaces
- [x] No “backward compatibility” wording remains in `src/erdos/`
- [x] `make ci` passes
