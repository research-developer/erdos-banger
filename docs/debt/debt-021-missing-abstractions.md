# Technical Debt 021: Missing Abstractions

**Date:** 2026-01-19
**Status:** Open
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Extensibility, testability, separation of concerns

## Summary

The codebase lacks several standard architectural patterns that would improve organization and testability. Key missing abstractions include Repository pattern, Service layer, and proper separation between I/O and business logic.

## Missing Patterns

### 1. No Repository Pattern

**Current State:**

`ProblemLoader` does everything:
- Path resolution (finding data files)
- File I/O (reading YAML)
- Parsing (YAML to dict)
- Validation (Pydantic models)
- Caching (in-memory)
- Filtering (query logic)

```python
class ProblemLoader:
    def __init__(self, yaml_path: Path): ...
    def from_default(cls): ...          # Path resolution
    def _load_raw(self): ...            # File I/O + parsing
    def _parse_problem(self, raw): ...  # Validation
    def load_all(self): ...             # Caching
    def filter(self, **criteria): ...   # Query logic
```

**Problem:** Testing filtering logic requires file system access. Can't test caching without parsing. Can't swap data source without changing everything.

**Desired State:**

```python
# Repository interface (abstract)
class ProblemRepository(Protocol):
    def get_by_id(self, id: int) -> ProblemRecord | None: ...
    def get_all(self) -> list[ProblemRecord]: ...
    def filter(self, criteria: FilterCriteria) -> list[ProblemRecord]: ...

# Concrete implementations
class YamlProblemRepository(ProblemRepository):
    """Loads from YAML file."""

class InMemoryProblemRepository(ProblemRepository):
    """For testing."""

class CachedProblemRepository(ProblemRepository):
    """Decorator that adds caching to any repository."""
```

### 2. No Service Layer

**Current State:**

Commands call core functions directly:

```
CLI Command → Core Function → Data Access → Response
```

```python
# commands/refs.py
def refs(ctx, problem_id, ...):
    loader = ProblemLoader.from_default()
    result = get_refs(problem_id, loader)  # Direct call
    exit_with_result(ctx, result)
```

**Problem:** Business logic (validation, orchestration) is split between commands and core functions. No central place for cross-cutting concerns.

**Desired State:**

```
CLI Command → Service → Repository → Response
```

```python
# services/problem_service.py
class ProblemService:
    def __init__(
        self,
        repo: ProblemRepository,
        index: SearchIndex,
    ):
        self.repo = repo
        self.index = index

    def get_problem(self, id: int) -> ProblemRecord | None:
        return self.repo.get_by_id(id)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self.index.search(query, limit=limit)

    def ask_question(self, problem_id: int, question: str) -> AskResult:
        problem = self.repo.get_by_id(problem_id)
        if not problem:
            raise ProblemNotFoundError(problem_id)
        sources = self._retrieve_sources(problem, question)
        prompt = self._build_prompt(problem, sources, question)
        return AskResult(problem=problem, sources=sources, prompt=prompt)
```

### 3. No Clear I/O Boundary

**Current State:**

I/O is mixed with business logic throughout:

```python
# core/ingest.py - I/O and logic interleaved
def ingest_problem_references(...):
    # Load problem (I/O)
    loader = ProblemLoader.from_default()
    problem = loader.get_by_id(problem_id)

    # Load manifest (I/O)
    if manifest_path.exists():
        with manifest_path.open() as f:
            manifest_data = yaml.safe_load(f)

    # Business logic mixed with I/O
    for ref in problem.references:
        if not ref.doi and not ref.arxiv_id:
            continue
        # Network I/O
        crossref_data = fetch_crossref_work(ref.doi, ...)
        # More business logic
        reference = parse_crossref_work(crossref_data, ...)
        # File I/O
        arxiv_cache_path.write_bytes(tarball_bytes)
```

**Problem:** Can't test business logic without mocking file system and network. Can't replace storage mechanism.

**Desired State:**

```python
# Ports (interfaces)
class MetadataFetcher(Protocol):
    def fetch_doi(self, doi: str) -> ReferenceRecord: ...
    def fetch_arxiv(self, arxiv_id: str) -> ReferenceRecord: ...

class ManifestStore(Protocol):
    def load(self, problem_id: int) -> ProblemManifest | None: ...
    def save(self, manifest: ProblemManifest) -> None: ...

# Core logic - no I/O
class IngestionService:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        store: ManifestStore,
        repo: ProblemRepository,
    ):
        self.fetcher = fetcher
        self.store = store
        self.repo = repo

    def ingest(self, problem_id: int) -> IngestionResult:
        # Pure business logic - I/O injected
        problem = self.repo.get_by_id(problem_id)
        existing = self.store.load(problem_id)
        # ... logic ...
        self.store.save(manifest)
```

### 4. No Value Objects for Complex Data

**Current State:**

Filter criteria passed as kwargs:

```python
def filter(
    self,
    *,
    status: ProblemStatus | None = None,
    prize_min: int | None = None,
    prize_max: int | None = None,
    tags: list[str] | None = None,
    formalized: bool | None = None,
) -> list[ProblemRecord]:
```

**Problem:** Can't add new filter criteria without changing signature. Hard to compose filters.

**Desired State:**

```python
@dataclass(frozen=True)
class ProblemFilter:
    status: ProblemStatus | None = None
    prize_min: int | None = None
    prize_max: int | None = None
    tags: frozenset[str] | None = None
    formalized: bool | None = None

    def matches(self, problem: ProblemRecord) -> bool:
        """Check if problem matches all criteria."""
        if self.status and problem.status != self.status:
            return False
        # ... etc
        return True

def filter(self, criteria: ProblemFilter) -> list[ProblemRecord]:
    return [p for p in self.get_all() if criteria.matches(p)]
```

## Architecture Comparison

### Current Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI Commands                      │
│  (list, show, refs, search, lean, ingest, ask)      │
└─────────────────────┬───────────────────────────────┘
                      │ direct calls
                      ▼
┌─────────────────────────────────────────────────────┐
│                   Core Functions                     │
│  (Mixed: business logic + I/O + data access)        │
└─────────────────────┬───────────────────────────────┘
                      │ direct calls
                      ▼
┌─────────────────────────────────────────────────────┐
│              ProblemLoader / SearchIndex             │
│  (Mixed: file I/O + parsing + caching + filtering)  │
└─────────────────────────────────────────────────────┘
```

### Proposed Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI Commands                      │
│  (Thin: parse args, call service, format output)    │
└─────────────────────┬───────────────────────────────┘
                      │ inject
                      ▼
┌─────────────────────────────────────────────────────┐
│                    Services                          │
│  (ProblemService, SearchService, IngestionService)  │
│  (Pure business logic, no I/O)                      │
└─────────────────────┬───────────────────────────────┘
                      │ inject
                      ▼
┌─────────────────────────────────────────────────────┐
│                   Repositories                       │
│  (ProblemRepository, ManifestStore, MetadataFetcher)│
│  (Abstract interfaces)                              │
└─────────────────────┬───────────────────────────────┘
                      │ implement
                      ▼
┌─────────────────────────────────────────────────────┐
│                  Adapters (I/O)                      │
│  (YamlRepo, SqliteIndex, CrossrefClient, etc.)     │
│  (Concrete implementations)                         │
└─────────────────────────────────────────────────────┘
```

## Proposed Implementation

### Phase 1: Define Protocols

```python
# core/ports.py
from typing import Protocol

class ProblemRepository(Protocol):
    def get_by_id(self, id: int) -> ProblemRecord | None: ...
    def get_all(self) -> list[ProblemRecord]: ...

class SearchIndex(Protocol):
    def search(self, query: str, limit: int) -> list[SearchResult]: ...
    def index_problem(self, problem: ProblemRecord) -> None: ...

class MetadataFetcher(Protocol):
    def fetch_by_doi(self, doi: str) -> ReferenceRecord: ...
    def fetch_by_arxiv(self, arxiv_id: str) -> ReferenceRecord: ...
```

### Phase 2: Create Services

```python
# services/problem_service.py
class ProblemService:
    def __init__(self, repo: ProblemRepository):
        self.repo = repo

    def get(self, id: int) -> ProblemRecord:
        problem = self.repo.get_by_id(id)
        if not problem:
            raise ProblemNotFoundError(id)
        return problem

    def list(self, filter: ProblemFilter) -> list[ProblemRecord]:
        return [p for p in self.repo.get_all() if filter.matches(p)]
```

### Phase 3: Adapt Existing Code

Keep existing `ProblemLoader` but make it implement `ProblemRepository`:

```python
class ProblemLoader(ProblemRepository):
    # Existing code unchanged
    # But now it satisfies the protocol
```

### Phase 4: Wire Dependencies

```python
# core/bootstrap.py
def create_app_context() -> AppContext:
    repo = ProblemLoader.from_default()
    index = SearchIndex.from_default()
    problem_service = ProblemService(repo)
    search_service = SearchService(index, repo)
    return AppContext(
        problem_service=problem_service,
        search_service=search_service,
    )
```

## Acceptance Criteria

- [ ] `ProblemRepository` protocol defined
- [ ] `SearchIndexProtocol` protocol defined
- [ ] At least one service class created (`ProblemService`)
- [ ] Existing classes implement protocols (backward compatible)
- [ ] Test suite includes in-memory repository for unit tests
- [ ] All existing tests pass

## Effort Estimate

High - this is architectural refactoring. Should be done incrementally over multiple PRs.

## References

- Robert C. Martin, "Clean Architecture"
- Martin Fowler, "Patterns of Enterprise Application Architecture" - Repository pattern
- Ports and Adapters (Hexagonal Architecture)
