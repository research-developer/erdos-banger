# Friction Report: Aristotle Onboarding Experience

**Date:** 2026-01-26
**Context:** First use of `erdos lean prove` with Aristotle API

## Issues Encountered

### 1. `aristotlelib` Not Auto-Installed (P3)

**Error:**
```
Error: Aristotle command not found: aristotle. Ensure aristotlelib is installed...
```

**Root cause:** `aristotlelib` is an optional dependency, not in `pyproject.toml [dependencies]`.

**Fix:** `uv pip install aristotlelib`

**Recommendation:** Add to optional deps group or document more prominently.

### 2. Background Shell Loses Environment (Not a Bug)

When running commands in background (`&`), environment variables from `source .env` aren't inherited because they're not `export`ed.

**Workaround:** Inline the variable: `VAR=value command` or use `export $(grep -v '^#' .env | xargs)`

**Note:** The `erdos` CLI correctly loads `.env` via `initialize_environment()` - this only affects raw shell background jobs.

### 3. Aristotle Cloud Service is Slow (Expected)

Aristotle runs on cloud infrastructure. Jobs queue and poll every 30 seconds. For Problem 848 (3 theorems), expected wait is several minutes.

**Status:** Normal behavior, not friction.

## Summary

- **Not bugs:** env loading works correctly; Aristotle latency is expected
- **Minor friction:** aristotlelib should be easier to discover/install
- **No code changes needed** - documentation improvement only
