# BUG-057: Exa CLI Ignores ERDOS_EXA_SEARCH_TYPE Config

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-31
**Component:** `src/erdos/commands/research/exa.py`

## Summary

The `erdos research exa search` CLI command ignores the `ERDOS_EXA_SEARCH_TYPE` environment variable. The config infrastructure was added in BUG-056, but the CLI entry point was not wired to use it.

## Evidence

In `src/erdos/commands/research/exa.py` lines 230-238:

```python
config = ExaConfig(
    api_key=app_ctx.config.exa_api_key,
    cache_ttl_hours=app_ctx.config.exa_cache_ttl_hours,
    cache_path=(...),
)
```

**Missing:** `search_type=app_ctx.config.exa_search_type`

## Steps to Reproduce

```bash
# Set env var
export ERDOS_EXA_SEARCH_TYPE=deep

# Run CLI - should use "deep" but uses "neural"
uv run erdos research exa search 74 "graph coloring" --max-results 3

# Verify by checking API payload (would need debug logging)
```

## Expected Behavior

The CLI should pass `app_ctx.config.exa_search_type` to `ExaConfig`, making the API use the configured search type.

## Actual Behavior

The CLI creates `ExaConfig` without `search_type`, causing it to default to `"neural"` regardless of the environment variable.

## Root Cause

BUG-056 fix was incomplete. Phases 1-2 (config + API wiring) were done, but Phase 3 (CLI wiring) was missed.

## Recommended Fix

```python
config = ExaConfig(
    api_key=app_ctx.config.exa_api_key,
    cache_ttl_hours=app_ctx.config.exa_cache_ttl_hours,
    cache_path=(...),
    search_type=app_ctx.config.exa_search_type,  # ADD THIS
)
```

## Impact

- Users cannot control Exa search type via environment variable through CLI
- "Deep" search (higher quality, 3x cost) is inaccessible
- Blocks research quality improvements for prize problems

## Related

- BUG-056: Exa uses basic neural search (partial fix - config added)
- SPEC-029: Exa Research Integration
