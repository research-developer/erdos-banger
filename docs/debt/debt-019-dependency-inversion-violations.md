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
# src/erdos/commands/refs.py
    start_time = time.perf_counter()
    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        result = CLIOutput.err(
            command="erdos refs",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )
        exit_with_result(ctx, result)
        return

    result = get_refs(problem_id, loader)
```

The **core functions** are correctly designed:
```python
def get_refs(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    """Core refs logic (testable)."""
```

But the **CLI layer** hardcodes construction. This means:
- Tests must control global state (env vars / CWD / importlib.resources) instead of injecting dependencies
- Can't swap implementations without modifying commands
- Configuration is scattered across `from_default()` methods

### Problem 2: `from_default()` Anti-Pattern

Multiple classes have `from_default()` factory methods with hardcoded logic:

```python
# src/erdos/core/problem_loader.py:53-100 - ProblemLoader.from_default() (48 lines)
# src/erdos/core/search_index.py:59-69 - SearchIndex.from_default() (11 lines)
```

This hardcodes:
- Environment variable names
- Default paths
- Fallback order

### Problem 3: No Dependency Container

There's no central place that wires dependencies together. Each command does its own wiring:

```python
# src/erdos/commands/search.py
    try:
        index = SearchIndex.from_default()

        # Check if index has data
        if index.problem_count() == 0:
            return CLIOutput.err(
                command="erdos search",
                error_type="IndexEmpty",
                message="Search index is empty. Run with --build-index to populate it.",
                code=0,  # Not really an error, just needs index built
            )

        results = index.search(query, limit=limit, problem_id=problem_id)

        # Enrich results with problem titles (best-effort; index can still be used
        # even if the source YAML isn't available in this environment).
        loader: ProblemLoader | None = None
        try:
            loader = ProblemLoader.from_default()
        except ProblemLoaderError:
            loader = None
```

### Problem 4: Core Functions Also Violate

Some core functions create dependencies internally:

```python
# src/erdos/core/ask.py
    # Load problem
    try:
        loader = ProblemLoader.from_default()
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    try:
        problem = loader.get_by_id(problem_id)
    except ProblemLoaderError as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="LoaderError",
            message=str(e),
            code=ExitCode.ERROR,
        )

    if problem is None:
        return CLIOutput.err(
            command="erdos ask",
            error_type="NotFound",
            message=f"Problem {problem_id} not found",
            code=ExitCode.NOT_FOUND,
        )

    # Build/rebuild index if requested
    if build_index_flag:
        try:
            build_index(loader=loader, rebuild=True)
        except Exception as e:
            return CLIOutput.err(
                command="erdos ask",
                error_type="ERROR",
                message=f"Failed to build index: {e}",
                code=ExitCode.ERROR,
            )

    # Get search index
    try:
        index = SearchIndex.from_default()
    except Exception as e:
        return CLIOutput.err(
            command="erdos ask",
            error_type="ERROR",
            message=f"Failed to open search index: {e}",
            code=ExitCode.ERROR,
        )
```

Compare to the correctly-designed `get_refs()`:
```python
def get_refs(problem_id: int, loader: ProblemLoader) -> CLIOutput:
    # Loader injected - can test with any implementation
```

## Violations by File

| File | Function | Creates |
|------|----------|---------|
| `src/erdos/commands/list_cmd.py` | `list_()` | `ProblemLoader.from_default()` |
| `src/erdos/commands/show.py` | `show()` | `ProblemLoader.from_default()` |
| `src/erdos/commands/refs.py` | `refs()` | `ProblemLoader.from_default()` |
| `src/erdos/commands/search.py` | `search()` | `ProblemLoader.from_default()` (fallback path) |
| `src/erdos/commands/search.py` | `search_problems_fts()` | `SearchIndex.from_default()`, `ProblemLoader.from_default()` (best-effort enrichment) |
| `src/erdos/commands/lean.py` | `formalize_problem()` | `ProblemLoader.from_default()` |
| `src/erdos/core/ingest.py` | `ingest_problem_references()` | `ProblemLoader.from_default()` |
| `src/erdos/core/ask.py` | `ask_question()` | `ProblemLoader.from_default()`, `SearchIndex.from_default()` |
| `src/erdos/core/index_builder.py` | `build_index()` | Defaults to both if args are `None` |

## Proposed Fix

### Phase 1: Define Protocols (Abstractions)

```python
# src/erdos/core/protocols.py (to create)
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
# src/erdos/core/context.py (to create)
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
# src/erdos/commands/refs.py
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
# src/erdos/core/ask.py
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
