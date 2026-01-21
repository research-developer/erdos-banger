# DEBT-038: MetadataProvider Abstraction Missing

**Status:** Open
**Priority:** P2
**Found:** 2026-01-21
**Found By:** API orchestration architecture review

---

## Summary

The codebase has separate clients for each metadata source (`arxiv_client.py`, `crossref_client.py`, `openalex_client.py`) but lacks a unified `MetadataProvider` protocol/interface. This violates:

1. **Dependency Inversion Principle (DIP)** - High-level ingest logic depends on concrete clients
2. **Open/Closed Principle (OCP)** - Adding new sources requires modifying existing code

---

## Current State

```
src/erdos/core/
├── arxiv_client.py      # ArxivClient class
├── crossref_client.py   # Functions: fetch_crossref_work(), parse_crossref_work()
├── openalex_client.py   # OpenAlexClient class
└── ingest/
    └── fetch.py         # Hardcoded if/elif for each source
```

The ingest pipeline in `fetch.py` has hardcoded source selection:

```python
# Current (DEBT-038)
if source == "openalex":
    client = OpenAlexClient()
    return client.get_by_doi(ref_id)
elif source == "arxiv":
    return parse_arxiv_atom(fetch_arxiv_atom(ref_id))
elif source == "crossref":
    payload = fetch_crossref_work(ref_id, mailto=mailto, timeout=timeout)
    return parse_crossref_work(payload, doi=ref_id)
```

---

## Desired State (Rob C. Martin Principles)

### MetadataProvider Protocol

```python
# src/erdos/core/ports.py (or ports/metadata.py)

from typing import Protocol
from erdos.core.models import ReferenceRecord

class MetadataProvider(Protocol):
    """Port for academic metadata sources (DIP)."""

    def get_by_doi(self, doi: str) -> ReferenceRecord:
        """Fetch work by DOI."""
        ...

    def get_by_arxiv(self, arxiv_id: str) -> ReferenceRecord:
        """Fetch work by arXiv ID."""
        ...

    def search(self, query: str, *, limit: int = 25) -> list[ReferenceRecord]:
        """Search works by title/abstract."""
        ...
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    High-Level Policy                         │
│                  (IngestService, AskService)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ depends on abstraction
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               MetadataProvider (Protocol/Port)              │
│  get_by_doi(doi) -> ReferenceRecord                         │
│  get_by_arxiv(arxiv_id) -> ReferenceRecord                  │
│  search(query) -> List[ReferenceRecord]                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ implemented by
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ OpenAlexProv │   │ CrossrefProv │   │  FutureProv  │
│  (Primary)   │   │  (Fallback)  │   │ (Pluggable)  │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Ingest With Provider

```python
# Desired state
def fetch_reference_metadata(
    ref_id: str,
    *,
    provider: MetadataProvider,  # Injected dependency
) -> ReferenceRecord:
    """Fetch reference metadata using the injected provider."""
    if is_doi(ref_id):
        return provider.get_by_doi(ref_id)
    elif is_arxiv_id(ref_id):
        return provider.get_by_arxiv(ref_id)
    else:
        raise ValueError(f"Unknown reference format: {ref_id}")
```

### Composition in AppContext

```python
# src/erdos/core/context.py
from erdos.core.openalex_client import OpenAlexClient
from erdos.core.crossref_client import CrossrefProvider

@dataclass
class AppContext:
    metadata_provider: MetadataProvider

    @classmethod
    def from_env(cls) -> AppContext:
        # OpenAlex as primary
        primary = OpenAlexClient.from_env()
        # Could add fallback chain: FallbackProvider(primary, CrossrefProvider())
        return cls(metadata_provider=primary)
```

---

## Benefits

1. **Testability** - Inject mock providers in tests
2. **Extensibility** - Add Semantic Scholar, Exa, zbMATH without modifying ingest code
3. **Clarity** - Clear separation of concerns
4. **Configuration** - Swap providers via config/env

---

## Implementation Steps

1. [ ] Create `MetadataProvider` protocol in `src/erdos/core/ports.py`
2. [ ] Update `OpenAlexClient` to implement `MetadataProvider`
3. [ ] Create `CrossrefProvider` wrapper that implements `MetadataProvider`
4. [ ] Update `AppContext` to compose/inject the provider
5. [ ] Refactor `ingest/fetch.py` to accept `MetadataProvider` instead of string source
6. [ ] Add `FallbackProvider` that chains providers (OpenAlex → Crossref)
7. [ ] Update tests to inject mock providers

---

## Acceptance Criteria

1. [ ] `MetadataProvider` protocol exists and is documented
2. [ ] OpenAlex and Crossref implement the protocol
3. [ ] Ingest service accepts provider via dependency injection
4. [ ] Tests use mock providers (no network calls in unit tests)
5. [ ] Adding a new source requires only: new provider + registration

---

## Related

- `BUG-018`: OpenAlex `get_by_arxiv()` is broken (must fix before this refactor)
- `SPEC-020`: OpenAlex integration spec
- `docs/specs/master-qualifications.md`: Section 5 (API Orchestration Strategy)

---

## References

- [Protocol classes in Python](https://peps.python.org/pep-0544/)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Ports and Adapters / Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
