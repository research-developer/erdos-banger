# Technical Debt 016: Single Responsibility Principle Violation in Domain Models

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** 3f63fab
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Maintainability, testability, cognitive load

## Summary

The domain model definitions originally lived in a single, monolithic module (`src/erdos/core/models.py`) containing unrelated concepts (problem data, search chunks, Lean errors, CLI output). This violated SRP and increased cognitive load and import bloat.

## Resolution

Split the monolith into focused modules under `src/erdos/core/models/` and re-exported from `src/erdos/core/models/__init__.py` to preserve the public import surface (`from erdos.core.models import ...`).

Current structure:

```text
src/erdos/core/models/
├── __init__.py          # re-exports (backward compatible)
├── base.py              # ErdosBaseModel, utc_now()
├── problem.py           # ProblemStatus, ReferenceEntry, ProblemRecord
├── reference.py         # ReferenceRecord, ManifestEntry, ProblemManifest, enums
├── search.py            # ChunkSource, TextChunk
├── lean.py              # LeanError, LeanCheckResult
└── output.py            # CLIOutput
```

## Verification

```bash
# Backward-compatible imports still work
uv run python -c "from erdos.core.models import ProblemRecord, CLIOutput; print('OK')"

# CI passes
make ci
```

## Acceptance Criteria

- [x] Models split into focused modules (`src/erdos/core/models/`)
- [x] All existing imports continue to work (`erdos.core.models`)
- [x] No circular imports
- [x] All tests pass (`make ci`)

## References

- Robert C. Martin, SOLID: Single Responsibility Principle
