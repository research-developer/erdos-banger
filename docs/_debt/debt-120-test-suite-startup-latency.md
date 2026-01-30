# DEBT-120: Test Suite Startup Latency

**Priority:** P4
**Status:** Open
**Found:** 2026-01-29
**Component:** `tests/`

## Summary

The test suite appears to "hang" for ~20-30 seconds before tests start flowing. This is expected behavior, not a bug, but worth documenting.

## Analysis

### Collection Phase (~10 seconds)
```bash
$ time uv run pytest --collect-only -q 2>&1 | tail -3
======================== 1834 tests collected in 9.77s =========================
```
Importing 1834 test modules takes ~10 seconds. This is normal for a large test suite.

### E2E Test Subprocess Overhead (~6 seconds each)
```bash
$ time uv run erdos --version
erdos-banger 0.1.0
uv run erdos --version  3.48s user 0.90s system 71% cpu 6.131 total
```

Each `uv run erdos` invocation incurs:
- uv virtual environment resolution
- Python interpreter startup
- Module imports (typer, rich, pydantic, etc.)

E2E tests in `tests/e2e/` spawn real CLI subprocesses, so 6 tests × 6 seconds = 36 seconds just for `test_cli_ask.py`.

### Total Perceived "Hang"
- Collection: ~10 seconds
- First E2E tests: ~30 seconds
- **Total before tests "flow":** ~40 seconds

## Why This Isn't a Bug

1. E2E tests intentionally spawn real subprocesses for realistic testing
2. Unit tests use `CliRunner` (in-process) and are fast
3. The test suite is working correctly, just with expected startup latency

## Potential Optimizations (Future)

### 1. Run Tests in Parallel (pytest-xdist)
```bash
uv run pytest -n auto  # Use all CPU cores
```
**Trade-off:** May need test isolation work; some tests share temp directories.

### 2. Reorder Tests (Fast First)
```toml
# pyproject.toml
testpaths = ["tests/unit", "tests/integration", "tests/e2e"]
```
Unit tests run first, giving faster feedback.

### 3. Mark E2E Tests as Slow
```python
@pytest.mark.slow
class TestErdosAsk:
    ...
```
Then default runs skip them: `pytest -m "not slow"`

### 4. Profile Import Time
```bash
python -X importtime -c "import erdos" 2>&1 | head -30
```
Identify slow imports that could be lazy-loaded.

## Recommendation

P4 priority - the current behavior is correct and the test suite passes. These optimizations would improve DX but aren't blocking anything.

## Related

- pytest-xdist for parallel test execution
- pytest-sugar for progress visualization (already installed)
