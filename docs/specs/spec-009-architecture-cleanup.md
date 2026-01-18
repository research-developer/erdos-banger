# Spec 009: Architecture Cleanup

> Refactors the codebase to follow Clean Architecture (Uncle Bob) principles before v1.1 feature development.

---

## Overview

The current codebase has grown organically and contains several architectural violations that will impede future development. This spec defines the refactoring needed to establish clear boundaries between layers.

### Why Now?

Analysis of archived bugs (BUG-001 through BUG-005) and debt items (DEBT-001 through DEBT-005) reveals patterns:

1. **Output contamination** - CLI concerns (`CLIOutput`) mixed into domain layer
2. **Duplicated code** - `_output()` function repeated in all 5 command files
3. **No abstractions** - Commands directly instantiate concrete infrastructure classes
4. **Folder confusion** - `core/` mixes domain models with infrastructure (file I/O, SQLite)

Fixing these now prevents compounding technical debt as v1.1 features (ingest, ask) are added.

### Guiding Principles

1. **Dependency Rule** - Dependencies point inward (domain has no external dependencies)
2. **Interface Segregation** - Small, focused protocols over large classes
3. **Single Responsibility** - Each module has one reason to change
4. **Incremental Migration** - Refactor in testable steps, never break CI

---

## 1) Current Architecture Audit

### Directory Structure (Before)

```
src/erdos/
├── cli.py                  # Entry point ✓
├── commands/               # Presentation layer ✓
│   ├── list_cmd.py        # Has _output(), uses concrete ProblemLoader
│   ├── show.py            # Has _output(), uses concrete ProblemLoader
│   ├── refs.py            # Has _output(), uses concrete ProblemLoader
│   ├── search.py          # Has _output(), uses SearchIndex + ProblemLoader
│   └── lean.py            # Has _output(), uses LeanRunner + Formalizer
└── core/                   # PROBLEM: Mixed concerns
    ├── models.py          # Domain + CLIOutput (violation!)
    ├── problem_loader.py  # Infrastructure (YAML file I/O)
    ├── search_index.py    # Infrastructure (SQLite FTS5)
    ├── index_builder.py   # Application service
    ├── formalizer.py      # Infrastructure (Jinja2 templates)
    ├── lean_runner.py     # Infrastructure (subprocess)
    └── exit_codes.py      # CLI concern (wrong location)
```

### Specific Violations

| Location | Issue | Impact |
|----------|-------|--------|
| `models.py:397-463` | `CLIOutput` in domain layer | Domain depends on presentation concerns |
| `models.py` | 466 lines, 12+ classes | Hard to navigate, multiple reasons to change |
| `commands/*.py` | Duplicated `_output()` function | DRY violation, inconsistent behavior risk |
| `commands/*.py` | Direct `ProblemLoader.from_default()` calls | Untestable without file system |
| `core/exit_codes.py` | CLI exit codes in core | Should be in commands layer |
| No `ports/` layer | Commands coupled to concrete implementations | Can't swap implementations for testing |

---

## 2) Target Architecture

### Directory Structure (After)

```
src/erdos/
├── cli.py                      # Entry point
├── commands/                   # Presentation layer
│   ├── __init__.py
│   ├── output.py               # CLIOutput (moved from models)
│   ├── presenter.py            # Shared _output() logic (extracted)
│   ├── exit_codes.py           # Exit codes (moved from core)
│   ├── list_cmd.py
│   ├── show.py
│   ├── refs.py
│   ├── search.py
│   └── lean.py
├── domain/                     # Pure domain models (no I/O)
│   ├── __init__.py
│   ├── problem.py              # ProblemRecord, ProblemStatus
│   ├── reference.py            # ReferenceEntry, ReferenceRecord
│   ├── manifest.py             # ManifestEntry, ProblemManifest
│   ├── search.py               # TextChunk, ChunkSource
│   └── lean.py                 # LeanError, LeanCheckResult
├── application/                # Use cases / orchestration
│   ├── __init__.py
│   ├── problem_service.py      # Get, list, filter problems
│   └── search_service.py       # Search with fallback logic
├── infrastructure/             # External concerns
│   ├── __init__.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── yaml_loader.py      # ProblemLoader implementation
│   ├── indexes/
│   │   ├── __init__.py
│   │   ├── sqlite_index.py     # SearchIndex implementation
│   │   └── builder.py          # Index building logic
│   └── lean/
│       ├── __init__.py
│       ├── runner.py           # LeanRunner
│       └── formalizer.py       # Skeleton generation
├── ports/                      # Abstractions (protocols)
│   ├── __init__.py
│   ├── problem_repository.py   # Protocol for problem access
│   └── searcher.py             # Protocol for search operations
└── templates/                  # Jinja2 templates (unchanged)
    └── lean_skeleton.j2
```

### Layer Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                      commands/                               │
│  (CLI, output formatting, user interaction)                  │
├─────────────────────────────────────────────────────────────┤
│                      application/                            │
│  (Use cases, orchestration, business logic)                  │
├─────────────────────────────────────────────────────────────┤
│         ports/                    domain/                    │
│  (Abstractions/Protocols)    (Pure data models)              │
├─────────────────────────────────────────────────────────────┤
│                      infrastructure/                         │
│  (File I/O, SQLite, subprocesses, external APIs)             │
└─────────────────────────────────────────────────────────────┘

Arrows point INWARD only:
- commands → application → ports/domain
- infrastructure → ports/domain
- Never: domain → infrastructure
```

---

## 3) Refactoring Steps

### Step 1: Extract CLIOutput to commands/output.py

**Before:** `core/models.py` contains `CLIOutput`

**After:** `commands/output.py` contains `CLIOutput`

```python
# src/erdos/commands/output.py
"""CLI output wrapper for consistent JSON formatting."""

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class CLIOutput(BaseModel):
    """
    Standard wrapper for CLI JSON output.

    All --json output uses this structure for consistency.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    schema_version: Annotated[int, Field(default=1)] = 1
    command: Annotated[str, Field(description="Command that produced this output")]
    success: Annotated[bool, Field(default=True)] = True
    data: Annotated[Any, Field(description="Command-specific output data")]
    error: Annotated[dict[str, Any] | None, Field(default=None)] = None
    timestamp: Annotated[datetime, Field(default_factory=utc_now)] = Field(
        default_factory=utc_now
    )
    duration_ms: Annotated[int | None, Field(default=None)] = None

    @model_validator(mode="after")
    def _check_invariants(self) -> "CLIOutput":
        """Ensure success/data/error consistency."""
        if self.success:
            if self.error is not None:
                raise ValueError("CLIOutput: success=True but error is set")
            return self

        if self.error is None:
            raise ValueError("CLIOutput: success=False but error is None")
        if self.data is not None:
            raise ValueError("CLIOutput: success=False but data is not None")

        required_keys = {"type", "message", "code"}
        missing = required_keys.difference(self.error.keys())
        if missing:
            raise ValueError(f"CLIOutput: error missing keys: {sorted(missing)}")

        return self

    @classmethod
    def ok(cls, command: str, data: Any, duration_ms: int | None = None) -> "CLIOutput":
        """Create a successful output."""
        return cls(command=command, success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def err(
        cls,
        command: str,
        error_type: str,
        message: str,
        code: int = 1,
    ) -> "CLIOutput":
        """Create an error output."""
        return cls(
            command=command,
            success=False,
            data=None,
            error={"type": error_type, "message": message, "code": code},
        )
```

**Migration:** Add re-export in `core/models.py` for backward compatibility:

```python
# src/erdos/core/models.py (temporary, remove after all imports updated)
from erdos.commands.output import CLIOutput as CLIOutput  # Re-export for compat
```

### Step 2: Extract Shared Presenter Logic

**Before:** Each command file has its own `_output()` function (5 copies)

**After:** Single `presenter.py` with shared logic

```python
# src/erdos/commands/presenter.py
"""Shared presentation logic for CLI commands."""

from typing import Any, cast

import typer
from rich.console import Console

from erdos.commands.output import CLIOutput


console = Console()
err_console = Console(stderr=True)


def output_result(ctx: typer.Context, result: CLIOutput) -> None:
    """
    Output a CLIOutput result based on format preference.

    Args:
        ctx: Typer context (checks ctx.obj["json"] for JSON mode)
        result: The CLIOutput to display
    """
    json_mode = (ctx.obj or {}).get("json", False)

    if json_mode:
        console.print_json(result.model_dump_json())
    elif result.success:
        # Delegate to command-specific human formatter
        # Each command registers its formatter
        pass
    else:
        error = cast(dict[str, Any], result.error)
        err_console.print(f"[red]Error:[/red] {error['message']}")


def exit_with_result(ctx: typer.Context, result: CLIOutput) -> None:
    """
    Output result and exit with appropriate code.

    Args:
        ctx: Typer context
        result: The CLIOutput to display
    """
    output_result(ctx, result)

    if not result.success:
        error = cast(dict[str, Any], result.error)
        raise typer.Exit(code=int(error.get("code", 1)))
```

### Step 3: Create Ports (Protocols)

```python
# src/erdos/ports/problem_repository.py
"""Protocol for problem data access."""

from typing import Protocol

from erdos.domain.problem import ProblemRecord, ProblemStatus


class ProblemRepository(Protocol):
    """
    Abstract interface for accessing problem data.

    Implementations:
    - YamlProblemLoader: Reads from YAML files
    - (Future) ApiProblemLoader: Fetches from remote API
    """

    def get_by_id(self, problem_id: int) -> ProblemRecord | None:
        """Get a single problem by ID."""
        ...

    def load_all(self) -> list[ProblemRecord]:
        """Load all problems."""
        ...

    def filter(
        self,
        *,
        status: ProblemStatus | None = None,
        prize_min: int | None = None,
        prize_max: int | None = None,
        tags: list[str] | None = None,
    ) -> list[ProblemRecord]:
        """Filter problems by criteria."""
        ...
```

```python
# src/erdos/ports/searcher.py
"""Protocol for search operations."""

from typing import Protocol

from erdos.domain.search import ChunkSource


class SearchResult(Protocol):
    """A single search result."""

    chunk_id: str
    snippet: str
    score: float
    source_type: ChunkSource
    problem_id: int | None
    reference_doi: str | None


class Searcher(Protocol):
    """
    Abstract interface for search operations.

    Implementations:
    - SqliteSearchIndex: FTS5-based search
    - (Future) VectorSearchIndex: Embedding-based search
    """

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        problem_id: int | None = None,
    ) -> list[SearchResult]:
        """Search for matching content."""
        ...

    def problem_count(self) -> int:
        """Return number of indexed problems."""
        ...
```

### Step 4: Split models.py into Domain Modules

**Before:** Single 466-line `models.py`

**After:** Focused modules by domain concept

```python
# src/erdos/domain/__init__.py
"""Domain models for erdos-banger."""

from erdos.domain.problem import ProblemRecord, ProblemStatus, ReferenceEntry
from erdos.domain.reference import OpenAccessStatus, ReferenceRecord
from erdos.domain.manifest import ManifestEntry, ProblemManifest
from erdos.domain.search import ChunkSource, TextChunk
from erdos.domain.lean import LeanError, LeanCheckResult

__all__ = [
    "ProblemRecord",
    "ProblemStatus",
    "ReferenceEntry",
    "OpenAccessStatus",
    "ReferenceRecord",
    "ManifestEntry",
    "ProblemManifest",
    "ChunkSource",
    "TextChunk",
    "LeanError",
    "LeanCheckResult",
]
```

```python
# src/erdos/domain/problem.py
"""Problem domain models."""

import re
from enum import Enum
from typing import Annotated

from pydantic import ConfigDict, Field

from erdos.domain.base import ErdosBaseModel


class ProblemStatus(str, Enum):
    """Status of an Erdős problem."""

    OPEN = "open"
    PROVED = "proved"
    DISPROVED = "disproved"
    PARTIALLY_SOLVED = "partially_solved"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "ProblemStatus":
        """Parse status from various string formats."""
        normalized = value.lower().strip()
        normalized = re.sub(r"\s*\([^)]*\)\s*$", "", normalized)
        normalized = normalized.replace("-", "_").replace(" ", "_")
        try:
            return cls(normalized)
        except ValueError:
            mapping = {
                "solved": cls.PROVED,
                "partial": cls.PARTIALLY_SOLVED,
                "open_problem": cls.OPEN,
            }
            return mapping.get(normalized, cls.UNKNOWN)


class ReferenceEntry(ErdosBaseModel):
    """A reference as embedded in a ProblemRecord."""

    model_config = ConfigDict(frozen=True)

    key: Annotated[str, Field(min_length=1, description="Reference key")]
    citation: Annotated[str | None, Field(default=None)] = None
    doi: Annotated[str | None, Field(default=None, pattern=r"^10\.\d{4,}/.*$")] = None
    arxiv_id: Annotated[str | None, Field(default=None)] = None
    url: Annotated[str | None, Field(default=None)] = None


class ProblemRecord(ErdosBaseModel):
    """An Erdős problem from the dataset."""

    model_config = ConfigDict(frozen=True)

    id: Annotated[int, Field(ge=1, description="Problem ID")]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    statement: Annotated[str, Field(min_length=1)]
    status: ProblemStatus
    prize: Annotated[int, Field(ge=0, default=0)] = 0
    tags: Annotated[list[str], Field(default_factory=list)] = Field(default_factory=list)
    references: Annotated[list[ReferenceEntry], Field(default_factory=list)] = Field(
        default_factory=list
    )
    oeis_ids: Annotated[list[str], Field(default_factory=list)] = Field(default_factory=list)
    notes: Annotated[str | None, Field(default=None)] = None
    formalized: Annotated[bool, Field(default=False)] = False

    def __str__(self) -> str:
        prize_str = f" (${self.prize})" if self.prize > 0 else ""
        return f"Problem {self.id}: {self.title}{prize_str} [{self.status.value}]"
```

### Step 5: Move Exit Codes

```python
# src/erdos/commands/exit_codes.py
"""Exit codes for CLI commands."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for erdos CLI."""

    SUCCESS = 0
    ERROR = 1
    USAGE_ERROR = 2
    NOT_FOUND = 3
    NETWORK_ERROR = 4
    LEAN_ERROR = 5
    CONFIG_ERROR = 10
```

---

## 4) Backward Compatibility

During migration, maintain imports via re-exports:

```python
# src/erdos/core/models.py (transition period)
"""
Domain models for erdos-banger.

DEPRECATED: Import from erdos.domain or erdos.commands.output instead.
This module re-exports for backward compatibility and will be removed
in a future version.
"""

import warnings

# Re-export domain models
from erdos.domain import (
    ChunkSource,
    LeanCheckResult,
    LeanError,
    ManifestEntry,
    OpenAccessStatus,
    ProblemManifest,
    ProblemRecord,
    ProblemStatus,
    ReferenceEntry,
    ReferenceRecord,
    TextChunk,
)

# Re-export CLI output (with deprecation warning in future)
from erdos.commands.output import CLIOutput

__all__ = [
    "ChunkSource",
    "CLIOutput",
    "LeanCheckResult",
    "LeanError",
    "ManifestEntry",
    "OpenAccessStatus",
    "ProblemManifest",
    "ProblemRecord",
    "ProblemStatus",
    "ReferenceEntry",
    "ReferenceRecord",
    "TextChunk",
]


def __getattr__(name: str):
    """Emit deprecation warning for direct imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from erdos.core.models is deprecated. "
            f"Use erdos.domain or erdos.commands.output instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

## 5) Verification: This Spec is Testable

### Unit Tests

```python
# tests/unit/test_architecture.py
"""Tests for architectural boundaries."""

import ast
import importlib
from pathlib import Path

import pytest


class TestLayerDependencies:
    """Verify dependency rule: dependencies point inward only."""

    def test_domain_has_no_infrastructure_imports(self) -> None:
        """Domain layer must not import from infrastructure."""
        domain_path = Path("src/erdos/domain")
        forbidden = {"erdos.infrastructure", "erdos.commands", "erdos.application"}

        for py_file in domain_path.glob("*.py"):
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(
                            alias.name.startswith(f) for f in forbidden
                        ), f"{py_file.name} imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        assert not any(
                            node.module.startswith(f) for f in forbidden
                        ), f"{py_file.name} imports from {node.module}"

    def test_ports_has_no_infrastructure_imports(self) -> None:
        """Ports layer must not import from infrastructure."""
        ports_path = Path("src/erdos/ports")
        forbidden = {"erdos.infrastructure", "erdos.commands"}

        for py_file in ports_path.glob("*.py"):
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not any(
                        node.module.startswith(f) for f in forbidden
                    ), f"{py_file.name} imports from {node.module}"


class TestCLIOutputLocation:
    """Verify CLIOutput is in the right place."""

    def test_cli_output_importable_from_commands(self) -> None:
        """CLIOutput should be importable from commands.output."""
        from erdos.commands.output import CLIOutput

        assert CLIOutput is not None

    def test_cli_output_not_in_domain(self) -> None:
        """CLIOutput should not be defined in domain layer."""
        domain_path = Path("src/erdos/domain")

        for py_file in domain_path.glob("*.py"):
            content = py_file.read_text()
            assert "class CLIOutput" not in content, f"CLIOutput found in {py_file.name}"


class TestPresenterExtraction:
    """Verify shared presenter logic is extracted."""

    def test_no_duplicate_output_functions(self) -> None:
        """Commands should not define their own _output functions."""
        commands_path = Path("src/erdos/commands")

        for py_file in commands_path.glob("*.py"):
            if py_file.name in ("presenter.py", "output.py", "__init__.py"):
                continue

            content = py_file.read_text()
            # Allow import of output_result, but not local def _output
            assert "def _output(" not in content, (
                f"{py_file.name} has local _output function. "
                "Use presenter.output_result instead."
            )
```

### Integration Tests

```python
# tests/integration/test_architecture_integration.py
"""Integration tests for architecture refactoring."""

import subprocess


class TestBackwardCompatibility:
    """Verify backward-compatible imports still work."""

    def test_models_reexports_work(self) -> None:
        """Old imports from core.models should still work."""
        # This tests the transition period re-exports
        code = """
from erdos.core.models import ProblemRecord, CLIOutput
print(ProblemRecord.__name__)
print(CLIOutput.__name__)
"""
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ProblemRecord" in result.stdout
        assert "CLIOutput" in result.stdout

    def test_new_imports_work(self) -> None:
        """New canonical imports should work."""
        code = """
from erdos.domain import ProblemRecord
from erdos.commands.output import CLIOutput
print(ProblemRecord.__name__)
print(CLIOutput.__name__)
"""
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestProtocolImplementations:
    """Verify infrastructure implements protocols."""

    def test_yaml_loader_implements_repository(self) -> None:
        """YamlProblemLoader should implement ProblemRepository."""
        from erdos.infrastructure.loaders.yaml_loader import YamlProblemLoader
        from erdos.ports.problem_repository import ProblemRepository

        # Check protocol methods exist
        assert hasattr(YamlProblemLoader, "get_by_id")
        assert hasattr(YamlProblemLoader, "load_all")
        assert hasattr(YamlProblemLoader, "filter")
```

### Acceptance Criteria

```bash
# 1. All tests pass after refactoring
uv run pytest tests/ -v

# 2. Architecture tests specifically pass
uv run pytest tests/unit/test_architecture.py -v

# 3. Type checking passes
uv run mypy src/erdos/

# 4. No circular imports
python -c "import erdos.cli"

# 5. Backward compatibility maintained
python -c "from erdos.core.models import CLIOutput, ProblemRecord"

# 6. New canonical imports work
python -c "from erdos.domain import ProblemRecord; from erdos.commands.output import CLIOutput"

# 7. CLI still works
uv run erdos list --limit 5
uv run erdos show 6
uv run erdos search "prime"
```

---

## 6) Migration Order

Execute refactoring in this order to maintain CI green throughout:

| Step | Change | Risk | Rollback |
|------|--------|------|----------|
| 1 | Create `commands/output.py` with `CLIOutput` | Low | Delete file |
| 2 | Add re-export in `core/models.py` | Low | Remove re-export |
| 3 | Create `commands/presenter.py` | Low | Delete file |
| 4 | Create `domain/` with split models | Medium | Delete folder |
| 5 | Create `ports/` with protocols | Low | Delete folder |
| 6 | Update `core/models.py` to re-export from domain | Medium | Revert file |
| 7 | Create `infrastructure/` structure | Low | Delete folder |
| 8 | Move loaders/indexes to infrastructure | High | Revert moves |
| 9 | Update commands to use presenter | Medium | Revert commands |
| 10 | Update commands to use ports (DI) | High | Revert commands |
| 11 | Remove deprecated re-exports | Low | Re-add exports |

**Rule:** Run `uv run pytest` after each step. If tests fail, fix before proceeding.

---

## 7) Future Considerations

### Dependency Injection

After this refactoring, commands can accept repositories via dependency injection:

```python
# Future pattern for commands
def list_problems(
    *,
    status: str | None,
    limit: int,
    repository: ProblemRepository,  # Injected, not created internally
) -> CLIOutput:
    """List problems using injected repository."""
    problems = repository.filter(status=status)
    # ...
```

This enables:
- Easy testing with mock repositories
- Swapping implementations (YAML → API → Database)
- Composition root pattern in `cli.py`

### Service Layer

The `application/` layer enables complex use cases:

```python
# src/erdos/application/search_service.py
class SearchService:
    """Orchestrates search with fallback logic."""

    def __init__(
        self,
        searcher: Searcher,
        repository: ProblemRepository,
    ) -> None:
        self._searcher = searcher
        self._repository = repository

    def search_with_fallback(self, query: str, limit: int = 10) -> SearchResult:
        """Try FTS search, fall back to basic if index empty."""
        if self._searcher.problem_count() == 0:
            return self._basic_search(query, limit)
        return self._searcher.search(query, limit=limit)
```

---

## References

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-17 | Initial spec |
