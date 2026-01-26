# BUG-044: Environment Variables Not Auto-Loaded in Python Scripts

**Date:** 2026-01-26
**Severity:** P2 (Medium - confusing DX)
**Status:** Fixed (docs)
**Commit:** b43c3a7
**Component:** `erdos.core.config`

## Summary

When using erdos modules directly in Python (not via CLI), environment variables from `.env` are not loaded automatically. Users must call `initialize_environment()` first.

## Reproduction

```python
# This fails:
from erdos.core.clients.exa import ExaClient
client = ExaClient()
result = client.search("test")
# ValueError: EXA_API_KEY not set

# This works:
from erdos.core.config import initialize_environment
initialize_environment()  # Must call this first!
from erdos.core.clients.exa import ExaClient
client = ExaClient()
result = client.search("test")  # Works
```

## Root Cause

The `initialize_environment()` function loads `.env` via `python-dotenv`, but:
1. It's not called automatically on module import
2. Clients like `ExaClient` use `AppConfig.from_env()` which reads `os.environ`
3. If `.env` wasn't loaded, the env vars don't exist

## Impact

- Confusing for developers using the library
- Works in CLI (which calls `initialize_environment()`) but not in scripts
- Different behavior depending on entry point

## Expected Behavior

Options:
1. Auto-load `.env` on first `AppConfig.from_env()` call
2. Or document clearly that `initialize_environment()` must be called
3. Or use `python-dotenv`'s `load_dotenv(override=False)` at module level

## Note

The CLI correctly calls `initialize_environment()` in `cli.py`. This is only an issue for direct Python usage.
