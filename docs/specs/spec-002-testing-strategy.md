# Spec 002: Testing Strategy & Architecture

> Defines how we test erdos-harness: what to test, when to mock, and how to ensure vertical slices are testable end-to-end.

---

## Overview

This spec establishes the testing philosophy and patterns for the project. Every feature built must be testable. We follow TDD (Test-Driven Development) with a focus on behavior, not implementation details.

### Guiding Principles

1. **Test behavior, not implementation** - Tests should not break when refactoring internal code
2. **Minimal mocking** - Only mock what you can't control (external APIs, filesystem in some cases)
3. **Vertical slices** - Every feature is testable end-to-end from day one
4. **Fast feedback** - Unit tests run in milliseconds, the full suite in seconds
5. **No flaky tests** - Tests must be deterministic and reproducible

---

## 1) Test Pyramid: Our Distribution

```
        /\
       /  \         E2E Tests (10-15%)
      /----\        - Full CLI invocations
     /      \       - Real filesystem, real data
    /--------\      Integration Tests (30-35%)
   /          \     - Multiple components together
  /------------\    - Real dependencies where practical
 /              \   Unit Tests (50-55%)
/----------------\  - Single function/class
                    - Pure logic, no I/O
```

### Concrete Numbers

For v1.0, targeting approximately:
- **Unit tests:** 50-60 tests
- **Integration tests:** 30-40 tests
- **E2E tests:** 10-15 tests

---

## 2) Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures for all tests
├── unit/
│   ├── __init__.py
│   ├── conftest.py             # Unit-specific fixtures
│   ├── test_models.py          # Domain model tests
│   ├── test_problem_loader.py  # YAML parsing tests
│   └── test_lean_parser.py     # Lean error parsing tests
├── integration/
│   ├── __init__.py
│   ├── conftest.py             # Integration fixtures
│   ├── test_cli_commands.py    # CLI command integration
│   ├── test_search_index.py    # SQLite FTS integration
│   └── test_lean_runner.py     # Lean subprocess integration
└── e2e/
    ├── __init__.py
    ├── conftest.py             # E2E fixtures (temp directories, etc.)
    ├── test_full_workflow.py   # Complete user workflows
    └── test_cli_outputs.py     # CLI JSON/human output verification
```

---

## 3) pytest Configuration

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
minversion = "9.0"
addopts = [
    "-ra",                      # Show extra summary for all except passed
    "-q",                       # Quieter output
    "--strict-markers",         # Error on unknown markers
    "--strict-config",          # Error on config issues
    "--import-mode=importlib",  # Modern import mode for src layout
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "e2e: end-to-end tests requiring full environment",
    "requires_lean: tests that need Lean installed",
    "requires_network: tests that need network access",
]
filterwarnings = [
    "error",                    # Treat warnings as errors
    "ignore::DeprecationWarning:hypothesis.*",
]

[tool.coverage.run]
source = ["src"]
branch = true
parallel = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@overload",
]
fail_under = 80
show_missing = true
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=erdos --cov-report=term-missing

# Run only unit tests (fast)
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run E2E tests
uv run pytest tests/e2e/ -m e2e

# Skip slow tests
uv run pytest -m "not slow"

# Run in parallel (requires pytest-xdist)
uv run pytest -n auto

# Run specific test
uv run pytest tests/unit/test_models.py::test_problem_record_validates
```

---

## 4) What to Mock vs What Not to Mock

### The Golden Rule

> **Mock only what you cannot control or what makes tests unreliable.**

### Never Mock (Test Against Real Implementation)

| Component | Why Real |
|-----------|----------|
| Pydantic models | Validation logic IS the behavior |
| SQLite database | Use in-memory `:memory:` - fast and real |
| YAML parsing | Test against actual YAML files |
| Lean error parsing | Use captured real Lean output |
| CLI argument parsing | Typer/Click handles this - test the real thing |
| JSON serialization | Test actual output format |

### Mock Only When Necessary

| Component | When to Mock | How to Verify Mock is Correct |
|-----------|--------------|-------------------------------|
| External HTTP APIs (Crossref, arXiv) | Always in unit/integration tests | Record real responses, replay in tests |
| Lean subprocess execution | In unit tests only | Integration tests run real Lean |
| Filesystem (sometimes) | Only for isolation in unit tests | Integration tests use temp directories |
| System time | When testing time-dependent logic | Verify behavior matches real time |

### How to Verify Mocks Are Correct

Every mock must be validated against reality:

```python
# BAD: Mock with assumed behavior
def test_crossref_fetch(mocker):
    mocker.patch("erdos.core.ingest.fetch_crossref", return_value={"title": "Test"})
    # ... test that assumes this is what Crossref returns

# GOOD: Mock with recorded real response
def test_crossref_fetch(crossref_response_fixture):
    # crossref_response_fixture was recorded from an actual API call
    # and is stored in tests/fixtures/crossref_responses/
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.crossref.org/works/10.1234/test",
            json=crossref_response_fixture,
        )
        result = fetch_crossref("10.1234/test")
        assert result.title == "Actual Title From Real Response"
```

### Recording Real Responses

For external APIs, we record real responses once and replay them:

```
tests/
└── fixtures/
    ├── crossref_responses/
    │   ├── doi_10.1007_BF01940595.json  # Real response, recorded once
    │   └── doi_not_found.json
    ├── arxiv_responses/
    │   └── arxiv_2203.00001.xml
    └── lean_outputs/
        ├── successful_compile.txt
        └── type_error_line_42.txt
```

---

## 5) Fixture Strategy

### Shared Fixtures (`tests/conftest.py`)

```python
"""Shared fixtures for all tests."""

from pathlib import Path
from typing import Iterator

import pytest

from erdos.core.models import ProblemRecord


@pytest.fixture
def sample_problem() -> ProblemRecord:
    """A minimal valid ProblemRecord for testing."""
    return ProblemRecord(
        id=6,
        title="Test Problem",
        statement="Prove that P implies Q.",
        status="open",
        prize=100,
        tags=["number theory"],
        references=[],
    )


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_problems_yaml(fixtures_dir: Path) -> Path:
    """Path to sample problems.yaml for testing."""
    return fixtures_dir / "sample_problems.yaml"
```

### Unit Test Fixtures (`tests/unit/conftest.py`)

```python
"""Fixtures for unit tests - no I/O, no subprocesses."""

import pytest


@pytest.fixture
def lean_error_output() -> str:
    """Captured Lean error output for parsing tests."""
    return """
Erdos/Problem006.lean:12:5: error: unknown identifier 'Nat.prime'
Erdos/Problem006.lean:15:10: error: type mismatch
  has type
    Nat
  but is expected to have type
    Prop
"""
```

### Integration Test Fixtures (`tests/integration/conftest.py`)

```python
"""Fixtures for integration tests - real components, isolated environment."""

from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary project directory with required structure."""
    # Create minimal structure
    (tmp_path / "data" / "erdosproblems").mkdir(parents=True)
    (tmp_path / "formal" / "lean" / "Erdos").mkdir(parents=True)
    (tmp_path / "index").mkdir()
    (tmp_path / "logs").mkdir()

    yield tmp_path

    # Cleanup is automatic with tmp_path


@pytest.fixture
def in_memory_db():
    """SQLite in-memory database for search index tests."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()
```

### E2E Test Fixtures (`tests/e2e/conftest.py`)

```python
"""Fixtures for end-to-end tests - full CLI invocation."""

import subprocess
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def cli_runner(tmp_path: Path) -> Iterator[callable]:
    """Run CLI commands in an isolated environment."""
    def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["uv", "run", "erdos", *args],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"CLI failed with code {result.returncode}:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        return result

    yield run
```

---

## 6) Vertical Slice Testing Pattern

Every feature is built as a vertical slice: from user input to output, testable at each layer.

### Example: `erdos show` Command

```
User runs: erdos show 6 --json
         │
         ▼
┌─────────────────────┐
│    CLI Layer        │ ◄── E2E test: verify JSON output format
│   (Typer command)   │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   Command Logic     │ ◄── Integration test: command + loader together
│  (show.py module)   │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Problem Loader     │ ◄── Integration test: loads from real YAML
│ (problem_loader.py) │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   Domain Models     │ ◄── Unit test: validates, serializes correctly
│    (models.py)      │
└─────────────────────┘
```

### Tests for the Vertical Slice

```python
# tests/unit/test_models.py
def test_problem_record_to_json(sample_problem: ProblemRecord) -> None:
    """ProblemRecord serializes to expected JSON structure."""
    data = sample_problem.model_dump(mode="json")
    assert data["id"] == 6
    assert data["title"] == "Test Problem"
    assert "status" in data


# tests/integration/test_problem_loader.py
def test_loader_parses_real_yaml(sample_problems_yaml: Path) -> None:
    """ProblemLoader correctly parses the YAML format."""
    from erdos.core.problem_loader import ProblemLoader

    loader = ProblemLoader(sample_problems_yaml)
    problems = loader.load_all()

    assert len(problems) > 0
    assert all(isinstance(p, ProblemRecord) for p in problems)


# tests/integration/test_show_command.py
def test_show_returns_problem(sample_problems_yaml: Path) -> None:
    """show command returns correct problem data."""
    from erdos.commands.show import get_problem
    from erdos.core.problem_loader import ProblemLoader

    loader = ProblemLoader(sample_problems_yaml)
    result = get_problem(6, loader)
    assert result.success
    assert result.data["id"] == 6


# tests/e2e/test_cli_show.py
@pytest.mark.e2e
def test_erdos_show_json_output(cli_runner) -> None:
    """erdos show --json outputs valid JSON with expected fields."""
    result = cli_runner("show", "6", "--json")

    import json
    data = json.loads(result.stdout)

    assert data["success"] is True
    assert data["command"] == "erdos show"
    assert data["data"]["id"] == 6
    assert "title" in data["data"]
    assert "statement" in data["data"]
    assert "status" in data["data"]
```

---

## 7) Test-Driven Development Workflow

### The Red-Green-Refactor Cycle

```
1. RED:    Write a failing test for the behavior you want
2. GREEN:  Write the minimum code to make it pass
3. REFACTOR: Improve the code while keeping tests green
4. REPEAT
```

### Starting with an Integration Test

For new features, start with an integration or E2E test that defines the desired behavior:

```python
# Start here: what should happen when a user runs this?
def test_erdos_formalize_creates_lean_file(cli_runner, temp_project_dir):
    """erdos lean formalize should create a compilable Lean skeleton."""
    # This test will FAIL until we implement the feature
    result = cli_runner("lean", "formalize", "6")

    lean_file = temp_project_dir / "formal" / "lean" / "Erdos" / "Problem006.lean"
    assert lean_file.exists()
    assert "sorry" in lean_file.read_text()
    assert "theorem problem_6" in lean_file.read_text()
```

Then work backwards, writing unit tests for each component needed.

---

## 8) Property-Based Testing with Hypothesis

For domain models and parsing, use [Hypothesis](https://hypothesis.readthedocs.io/) to find edge cases.

```python
from hypothesis import given, strategies as st

from erdos.core.models import ProblemRecord


@given(
    id=st.integers(min_value=1, max_value=10000),
    title=st.text(min_size=1, max_size=200),
    status=st.sampled_from(["open", "proved", "disproved"]),
)
def test_problem_record_roundtrips(id: int, title: str, status: str) -> None:
    """ProblemRecord can be created and serialized with any valid inputs."""
    problem = ProblemRecord(
        id=id,
        title=title,
        statement="Test statement",
        status=status,
        prize=0,
        tags=[],
        references=[],
    )

    # Roundtrip through JSON
    data = problem.model_dump(mode="json")
    restored = ProblemRecord.model_validate(data)

    assert restored.id == problem.id
    assert restored.title == problem.title
    assert restored.status == problem.status
```

---

## 9) Testing External Dependencies

### Lean Subprocess Testing

```python
# tests/integration/test_lean_runner.py
import pytest
from pathlib import Path


@pytest.mark.requires_lean
def test_lean_check_compiles_valid_file(temp_lean_project: Path) -> None:
    """Lean runner successfully compiles a valid Lean file."""
    from erdos.core.lean_runner import LeanRunner

    # Create a valid Lean file
    lean_file = temp_lean_project / "Erdos" / "Test.lean"
    lean_file.write_text("theorem test : 1 + 1 = 2 := rfl\n")

    runner = LeanRunner(temp_lean_project)
    result = runner.check(lean_file)

    assert result.success
    assert len(result.errors) == 0


@pytest.mark.requires_lean
def test_lean_check_captures_errors(temp_lean_project: Path) -> None:
    """Lean runner captures and parses compile errors."""
    from erdos.core.lean_runner import LeanRunner

    # Create an invalid Lean file
    lean_file = temp_lean_project / "Erdos" / "Bad.lean"
    lean_file.write_text("theorem bad : 1 = 2 := rfl\n")  # This should fail

    runner = LeanRunner(temp_lean_project)
    result = runner.check(lean_file)

    assert not result.success
    assert len(result.errors) > 0
    assert any("type mismatch" in e.message for e in result.errors)
```

### Skipping Tests When Dependencies Missing

```python
import shutil

import pytest

lean_available = shutil.which("lean") is not None

@pytest.mark.skipif(not lean_available, reason="Lean not installed")
@pytest.mark.requires_lean
def test_that_needs_lean():
    ...
```

---

## 10) CI Test Matrix

**GitHub Actions workflow:**

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync

      - name: Run linting
        run: uv run ruff check .

      - name: Run type checking
        run: uv run mypy src/

      - name: Run tests
        run: uv run pytest --cov=erdos --cov-report=xml -m "not requires_lean"

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  test-with-lean:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true

      - name: Install elan and Lean
        run: |
          curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
          echo "$HOME/.elan/bin" >> $GITHUB_PATH

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Run Lean-dependent tests
        run: uv run pytest -m "requires_lean"
```

---

## 11) Verification: This Spec is Testable

### Acceptance Criteria

```bash
# All tests pass
uv run pytest
# Exit code: 0

# Coverage meets threshold
uv run pytest --cov=erdos --cov-fail-under=80
# Exit code: 0

# Tests are fast
uv run pytest tests/unit/ --durations=10
# Slowest unit test < 100ms

# Markers work correctly
uv run pytest -m "not requires_lean and not requires_network"
# Exit code: 0 (skips appropriate tests)
```

### Meta-Test: Testing the Testing Strategy

```python
# tests/test_test_infrastructure.py
"""Verify our testing infrastructure is correctly configured."""

from pathlib import Path

import pytest


def test_pytest_markers_are_registered() -> None:
    """All custom markers should be registered to avoid warnings."""
    # If markers aren't registered, pytest would warn
    # --strict-markers in config makes this a hard failure
    pass  # The fact this test runs without marker warnings is the test


def test_fixtures_directory_exists(fixtures_dir: Path) -> None:
    """Fixtures directory should exist and contain expected files."""
    assert fixtures_dir.exists()
    assert fixtures_dir.is_dir()


def test_in_memory_db_fixture_provides_connection(in_memory_db) -> None:
    """in_memory_db fixture should provide a working SQLite connection."""
    cursor = in_memory_db.execute("SELECT 1")
    assert cursor.fetchone() == (1,)
```

---

## 12) References

- [pytest Documentation](https://docs.pytest.org/en/stable/)
- [pytest Configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- [pytest Good Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Modern TDD in Python](https://testdriven.io/blog/modern-tdd/)
- [Python Testing Best Practices](https://pytest-with-eric.com/introduction/python-unit-testing-best-practices/)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-16 | Initial spec |
