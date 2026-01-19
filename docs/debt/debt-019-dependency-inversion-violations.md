# Technical Debt 019: Dependency Inversion Principle Violations

**Date:** 2026-01-19
**Status:** Open
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Testability, flexibility, coupling

## Summary

High-level modules (CLI commands) depend directly on low-level modules (concrete implementations). There is no abstraction layer, no dependency injection container, and dependencies are created inline rather than injected.

## The Principle

> "High-level modules should not depend on low-level modules. Both should depend on abstractions."
> — Robert C. Martin

## Current State

### Problem 1: Commands Create Their Own Dependencies

Every command creates its loader inline:

```python
# commands/refs.py
@app.callback(invoke_without_command=True)
def refs(ctx: typer.Context, problem_id: int, ...):
    # HIGH-LEVEL (command) creates LOW-LEVEL (loader)
    try:
        loader = ProblemLoader.from_default()  # ← Violation
    except ProblemLoaderError as e:
        ...

    result = get_refs(problem_id, loader)  # ← Good! Core takes dependency
```

The **core functions** are correctly designed:
```python
def get_refs(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    # Takes loader as parameter - testable!
```

But the **CLI layer** hardcodes construction. This means:
- Tests must mock `ProblemLoader.from_default()` instead of injecting
- Can't swap implementations without modifying commands
- Configuration is scattered across `from_default()` methods

### Problem 2: `from_default()` Anti-Pattern

Multiple classes have `from_default()` factory methods with hardcoded logic:

```python
# ProblemLoader.from_default() - 48 lines of path resolution
# SearchIndex.from_default() - 8 lines of path resolution
```

This hardcodes:
- Environment variable names
- Default paths
- Fallback order

### Problem 3: No Dependency Container

There's no central place that wires dependencies together. Each command does its own wiring:

```python
# commands/search.py
def search(...):
    loader = ProblemLoader.from_default()  # Created here
    index = SearchIndex.from_default()     # Created here too
    # No relationship between them
```

### Problem 4: Core Functions Also Violate

Some core functions create dependencies internally:

```python
# core/ask.py
def ask_question(...) -> CLIOutput:
    try:
        loader = ProblemLoader.from_default()  # ← Should be injected
    except ProblemLoaderError as e:
        ...

    try:
        index = SearchIndex.from_default()  # ← Should be injected
    except Exception as e:
        ...
```

Compare to the correctly-designed `get_refs()`:
```python
def get_refs(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    # Loader injected - can test with any implementation
```

## Violations by File

| File | Function | Creates |
|------|----------|---------|
| `commands/list_cmd.py` | `list_()` | `ProblemLoader.from_default()` |
| `commands/show.py` | `show()` | `ProblemLoader.from_default()` |
| `commands/refs.py` | `refs()` | `ProblemLoader.from_default()` |
| `commands/search.py` | `search()` | `ProblemLoader.from_default()` |
| `commands/lean.py` | `formalize()` | `ProblemLoader.from_default()` |
| `core/ingest.py` | `ingest_problem_references()` | `ProblemLoader.from_default()` |
| `core/ask.py` | `ask_question()` | `ProblemLoader.from_default()`, `SearchIndex.from_default()` |
| `core/index_builder.py` | `build_index()` | Both (with defaults) |

## Proposed Fix

### Phase 1: Define Protocols (Abstractions)

```python
# core/protocols.py
from typing import Protocol

class ProblemRepository(Protocol):
    """Abstract interface for problem data access."""

    def get_by_id(self, problem_id: int) -> ProblemRecord | None: ...
    def load_all(self) -> list[ProblemRecord]: ...
    def filter(self, **criteria) -> list[ProblemRecord]: ...

class SearchIndexProtocol(Protocol):
    """Abstract interface for search operations."""

    def search(self, query: str, limit: int = 10) -> list[SearchResult]: ...
    def index_problem(self, problem: ProblemRecord) -> None: ...
```

### Phase 2: Create Application Context

```python
# core/context.py
from dataclasses import dataclass

@dataclass
class AppContext:
    """Dependency container for the application."""

    loader: ProblemRepository
    index: SearchIndexProtocol | None = None

    @classmethod
    def from_environment(cls) -> "AppContext":
        """Create context from environment configuration."""
        loader = ProblemLoader.from_default()
        index = SearchIndex.from_default()
        return cls(loader=loader, index=index)
```

### Phase 3: Inject Context into Commands

```python
# commands/refs.py
def refs(ctx: typer.Context, problem_id: int, ...):
    # Get from application context (created once at startup)
    app_ctx = ctx.obj.get("app_context")
    if app_ctx is None:
        app_ctx = AppContext.from_environment()
        ctx.obj["app_context"] = app_ctx

    result = get_refs(problem_id, app_ctx.loader)
    exit_with_result(ctx, result, print_human=_print_human)
```

### Phase 4: Update Core Functions

```python
# core/ask.py
def ask_question(
    problem_id: int,
    question: str,
    *,
    loader: ProblemRepository,  # Injected
    index: SearchIndexProtocol,  # Injected
    ...
) -> CLIOutput:
    # No more from_default() calls inside
```

## Benefits

1. **Testability**: Inject mock repositories in tests
2. **Flexibility**: Swap implementations without modifying code
3. **Configuration**: Central place for wiring
4. **Clarity**: Dependencies are explicit in function signatures

## Acceptance Criteria

- [ ] `ProblemRepository` protocol defined
- [ ] `SearchIndexProtocol` defined
- [ ] `AppContext` container created
- [ ] All commands receive dependencies via context
- [ ] All core functions receive dependencies as parameters
- [ ] No `from_default()` calls inside business logic
- [ ] Tests can inject mock implementations
- [ ] All existing tests pass

## Effort Estimate

High - requires touching all commands and updating test fixtures.

## References

- Robert C. Martin, "Clean Code" Chapter 11: Systems
- SOLID Principles: Dependency Inversion Principle
- Martin Fowler, "Inversion of Control Containers and the Dependency Injection pattern"
