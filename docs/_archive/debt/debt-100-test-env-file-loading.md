# DEBT-100: Integration Tests Don't Load .env File

**Status:** Resolved
**Priority:** P3 (Tests skip instead of fail)
**Created:** 2026-01-24
**Resolved:** 2026-01-24
**Commit:** 8410c4f
**Related:** Exa integration tests, SPEC-029

## Problem

Integration tests that require API keys (e.g., `EXA_API_KEY`) skip with "key not set" even when the key is properly configured in `.env`.

## Evidence

```text
SKIPPED [1] tests/integration/test_exa_integration.py:47: EXA_API_KEY not set
SKIPPED [1] tests/integration/test_exa_integration.py:86: EXA_API_KEY not set
```

The `.env` file contains:

```ini
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

1. [x] Choose approach and implement → Option A (pytest-dotenv)
2. [x] `EXA_API_KEY` tests run when `.env` is present
3. [x] Document the approach in AGENTS.md testing section
4. [x] Ensure `.env` is still gitignored (no secrets in repo)

## Resolution

Implemented Option A (pytest-dotenv plugin):

1. Added `pytest-dotenv>=0.5.2` to dev dependencies
2. Configured `env_files = [".env"]` in `[tool.pytest.ini_options]`
3. Fixed tests expecting vars to be unset by explicitly setting them to `""`
4. Documented approach in AGENTS.md "API Keys for Network Tests" section
5. Verified `.env` is gitignored (line 41 of .gitignore)

**Note:** Click's CliRunner merges `env={}` with `os.environ`, so tests expecting
env vars to be absent must explicitly set them to empty strings.

## Effort Estimate

~20 minutes
