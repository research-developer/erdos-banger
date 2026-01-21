# DEBT-041: `ports.py` Leaks Concrete `search_index` Types (DIP Pressure)

**Status:** Open
**Priority:** P3
**Found:** 2026-01-21
**Found By:** Independent architecture review

---

## Summary

`src/erdos/core/ports.py` is intended to define **abstractions** (Protocols) that high-level code depends on. Today it imports concrete *implementation-module* types from `src/erdos/core/search_index.py` under `TYPE_CHECKING`:

- `EmbeddingModelProtocol`
- `SearchResult`
- `SemanticSearchResult`

Even though these imports are type-checking-only, they signal an architectural smell:

- **DIP pressure:** ports depend on an implementation module, not vice versa.
- **Refactor friction:** moving/renaming `search_index.py` forces churn in the “port” module.
- **Boundary ambiguity:** types that are part of the public contract live inside the concrete implementation.

---

## Evidence

`src/erdos/core/ports.py`:

```python
if TYPE_CHECKING:
    from erdos.core.search_index import (
        EmbeddingModelProtocol,
        SearchResult,
        SemanticSearchResult,
    )
```

---

## Recommended Fix (Clean Architecture)

Move the shared contract types to a stable, implementation-agnostic location, then have both the port and the implementation import from there.

Two viable placements:

### Option A (preferred): search-domain types module

- Create `src/erdos/core/search/types.py` containing:
  - `EmbeddingModelProtocol`
  - `SearchResult`
  - `SemanticSearchResult`
- Update:
  - `src/erdos/core/ports.py` to import from `erdos.core.search.types`
  - `src/erdos/core/search_index.py` to import from `erdos.core.search.types`

### Option B: move types into `core/models/`

- Move the same types into `src/erdos/core/models/search.py` (if you want “contract types live with models”).

---

## Acceptance Criteria

1. `src/erdos/core/ports.py` has **no imports** from `src/erdos/core/search_index.py`.
2. Contract types live in a shared module (e.g., `erdos.core.search.types`) and are imported by both ports + implementation.
3. `make ci` passes (ruff, mypy strict, pytest, coverage).
4. Existing import paths remain stable (either via re-export or a deliberate, documented breaking change).
