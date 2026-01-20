# Technical Debt 021: Missing Abstractions

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** 3dd1610
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Extensibility, testability, separation of concerns

## Summary

The codebase previously lacked lightweight, explicit abstractions for:

- Problem data access (so tests had to rely on filesystem-backed loaders).
- Simple “service/value object” patterns to keep command modules thin and behavior consistent.

This made it harder to unit test business logic without I/O and increased coupling between CLI and concrete implementations.

## Resolution

Added a minimal set of abstractions that match the current scope:

- Ports (interfaces): `src/erdos/core/ports.py`
  - `ProblemRepository`
  - `SearchIndexProtocol`
- In-memory repository for tests: `src/erdos/core/repositories.py` (`InMemoryProblemRepository`)
- Service/value objects: `src/erdos/services/problem_service.py`
  - `ProblemFilter` (value object)
  - `ProblemService` (use-cases for listing/getting problems)

Existing concrete implementations (e.g., `ProblemLoader`) satisfy the protocols via structural typing.

## Verification

```bash
# Protocols exist
test -f src/erdos/core/ports.py

# Service + in-memory repo exist
test -f src/erdos/services/problem_service.py
test -f src/erdos/core/repositories.py

# Unit tests cover the new service layer
uv run pytest tests/unit/test_problem_service.py -q
```

## Acceptance Criteria

- [x] `ProblemRepository` protocol defined (`src/erdos/core/ports.py`)
- [x] `SearchIndexProtocol` protocol defined (`src/erdos/core/ports.py`)
- [x] At least one service/value object introduced (`ProblemService`, `ProblemFilter`)
- [x] In-memory repository available for unit tests (`InMemoryProblemRepository`)
- [x] Tests pass (`make ci`)

## Notes (Out of Scope)

Additional abstractions like `MetadataFetcher`/`ManifestStore` are intentionally deferred to SPEC-010+ ingestion work; they are not required to satisfy this debt deck’s goal (unit-testable problem listing/querying and reduced CLI coupling).

## References

- Robert C. Martin, "Clean Architecture"
- Martin Fowler, "Patterns of Enterprise Application Architecture" (Repository)
