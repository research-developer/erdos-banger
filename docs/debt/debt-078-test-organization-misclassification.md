# DEBT-078: Test Organization — Misclassified Integration Test

**Priority:** P4 (Enhancement / polish)

**Status:** Open

## Problem

`tests/integration/test_show_command.py` is misclassified as an integration test when it's actually a unit test. It tests the `get_problem()` function directly with mocked dependencies, not through CLI invocation.

## Evidence

### 1. Test Content Analysis

**File:** `tests/integration/test_show_command.py` (28 lines)

```python
# Actual test pattern:
def test_show_valid_problem(sample_problem: ProblemRecord) -> None:
    loader = MagicMock(spec=ProblemLoader)
    loader.get_by_id.return_value = sample_problem
    result = get_problem(6, loader)  # Direct function call
    assert result.success
```

**Characteristics:**
- Calls `get_problem()` directly (not via CLI runner)
- Uses `MagicMock` for `ProblemLoader` (no real I/O)
- No subprocess invocation
- No file system interaction

### 2. Contrast with Actual Integration Tests

**File:** `tests/integration/test_cli_commands.py`

```python
def test_list_command(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(app, ["list", "--limit", "5"])  # CLI invocation
    assert result.exit_code == 0
```

Integration tests should:
- Invoke CLI via `CliRunner` or subprocess
- Exercise real I/O (file system, network, database)
- Test component boundaries

### 3. Duplicate Coverage

`tests/unit/commands/test_show.py` (26 lines) already tests the same function:

```python
def test_get_problem_not_found(mock_loader_empty: MagicMock) -> None:
    result = get_problem(999, mock_loader_empty)
    assert not result.success
```

Both files test `get_problem()` with mocked loaders — duplicate coverage.

## Proposed Fix

**Option A (Recommended):** Delete `tests/integration/test_show_command.py`
- The coverage is already provided by `tests/unit/commands/test_show.py`
- Reduces test suite noise

**Option B:** Move to Unit Tests
- Move `tests/integration/test_show_command.py` → `tests/unit/commands/`
- Merge with existing `test_show.py` if non-duplicate tests exist

### Verification

```bash
# Check coverage overlap
pytest tests/unit/commands/test_show.py tests/integration/test_show_command.py -v --collect-only
```

## Acceptance Criteria

- [ ] `tests/integration/test_show_command.py` removed or moved to `tests/unit/commands/`
- [ ] No loss of meaningful test coverage
- [ ] `make ci` passes

## Impact

- **Risk:** Very low (test file movement only)
- **Effort:** ~5 minutes
- **Benefit:** Clearer test organization, reduced confusion about test levels

## References

- Testing strategy: Integration tests should use CLI runner or real I/O
- `tests/unit/commands/test_show.py` (existing unit test)
