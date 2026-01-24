# DEBT-100: Integration Tests Don't Load .env File

**Status:** Open
**Priority:** P3 (Tests skip instead of fail)
**Created:** 2026-01-24
**Related:** Exa integration tests, SPEC-029

## Problem

Integration tests that require API keys (e.g., `EXA_API_KEY`) skip with "key not set" even when the key is properly configured in `.env`.

## Evidence

```
SKIPPED [1] tests/integration/test_exa_integration.py:47: EXA_API_KEY not set
SKIPPED [1] tests/integration/test_exa_integration.py:86: EXA_API_KEY not set
```

The `.env` file contains:
```
EXA_API_KEY=<redacted>
```
(Do not commit real keys; value redacted in this deck.)

Test code uses `os.environ.get("EXA_API_KEY")` which only sees shell environment variables, not `.env` contents.

## Root Cause

`pytest` doesn't automatically load `.env` files. The tests check `os.environ` at collection time before any potential dotenv loading.

## Fix Options

### Option A: pytest-dotenv plugin (Recommended)
Add `pytest-dotenv` to dev dependencies and configure in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
env_files = [".env"]
```

### Option B: Manual sourcing
Document that users must run `source .env && pytest ...` for network tests.

### Option C: conftest.py loading
Add dotenv loading to `tests/conftest.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Acceptance Criteria

1. [ ] Choose approach and implement
2. [ ] `EXA_API_KEY` tests run when `.env` is present
3. [ ] Document the approach in AGENTS.md testing section
4. [ ] Ensure `.env` is still gitignored (no secrets in repo)

## Effort Estimate

~20 minutes
