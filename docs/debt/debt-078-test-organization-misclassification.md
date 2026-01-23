# DEBT-078: Test Organization — Misleading “show command” Integration Test Name

**Priority:** P4 (Enhancement / polish)

**Status:** Open

## Problem

`tests/integration/test_show_command.py` is an **integration** test (it reads a real YAML fixture via `ProblemLoader`), but the file name is misleading:
- It is not a CLI test (no `CliRunner.invoke()`).
- It is not a unit test (it performs filesystem I/O + YAML parsing).

This creates confusion because most other `tests/integration/test_cli_*.py` files are CLI-level tests.

## Evidence

### 1. Test Content Analysis

**File:** `tests/integration/test_show_command.py`

```python
from erdos.commands.show import get_problem
from erdos.core.problem_loader import ProblemLoader

def test_show_real_problem(sample_problems_yaml: Path) -> None:
    loader = ProblemLoader(sample_problems_yaml)  # real file I/O + YAML parsing
    result = get_problem(6, loader)               # command core logic (not CLI)
    assert result.success
```

**Characteristics:**
- Calls `get_problem()` directly (core logic, not via CLI runner)
- Uses `ProblemLoader` against a real fixture file (filesystem I/O + YAML parsing)
- Exercises a meaningful boundary: loader + command-core behavior

### 2. Contrast with Actual Integration Tests

**File:** `tests/integration/test_cli_commands.py`

```python
def test_list_command(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["list", "--limit", "5"])  # CLI invocation
    assert result.exit_code == 0
```

CLI integration tests in this repo generally:
- Invoke CLI via `CliRunner` (in-process)
- Validate stdout/stderr/exit codes for user-facing behavior

### 3. Duplicate Coverage

`tests/unit/commands/test_show.py` (26 lines) already tests the same function:

```python
def test_get_problem_not_found(mock_loader_empty: MagicMock) -> None:
    result = get_problem(999, mock_loader_empty)
    assert not result.success
```

The unit tests cover the function with mocked repositories. The integration test adds coverage of `ProblemLoader` + YAML parsing + the `get_problem()` boundary. This is not pure duplication, but the naming is confusing.

## Proposed Fix

Rename the test file to reflect what it is:

- `tests/integration/test_show_command.py` → `tests/integration/test_show_loader_integration.py`

This keeps the test (useful coverage) but makes intent obvious.

### Verification

```bash
pytest tests/integration/test_show_loader_integration.py -v
```

## Acceptance Criteria

- [ ] Test file renamed to reflect loader integration (not CLI)
- [ ] `make ci` passes

## Impact

- **Risk:** Very low (test file rename only)
- **Effort:** ~5 minutes
- **Benefit:** Clearer test organization, reduced confusion about test levels

## References

- `tests/integration/test_cli_commands.py` (CLI integration tests)
- `tests/integration/test_show_command.py` (loader+core integration test)
- `tests/unit/commands/test_show.py` (unit tests)
