# Bug: `erdos ingest` ignores `--mailto`/`--timeout` for OpenAlex requests

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-23
**Fixed:** 2026-01-23
**Commit:** 853dde8

## Description

When `erdos ingest` runs with `--source openalex` (the default), the OpenAlex
provider was constructed via `OpenAlexProvider.from_env()`, which ignored the
CLI-provided `--mailto` and `--timeout` values.

This violates the principle of least surprise and makes it harder to run ingest
with per-invocation configuration (e.g., short timeouts in CI, custom mailto for
API polite pools).

## Steps to Reproduce

1. Run ingestion with a non-default timeout:
   - `erdos ingest 6 --timeout 1 --source openalex`
2. Observe that OpenAlex still uses its default timeout configuration.

## Expected Behavior

OpenAlex requests should use the `mailto` and `timeout` values derived from CLI
options (or their defaults), consistently with Crossref/arXiv providers.

## Actual Behavior

OpenAlex requests use environment-derived config and default timeouts, even when
CLI options provide different values.

## Root Cause

`src/erdos/core/ingest/fetch.py:_build_provider_from_source()` built OpenAlex via
`OpenAlexProvider.from_env()`, ignoring the `mailto` and `timeout` parameters it
already received.

## Fix

- Build `OpenAlexProvider` from an explicit `OpenAlexConfig`:
  - `email`/`timeout` come from CLI-derived values (or config defaults)
  - `api_key` comes from config/env
- Construct the provider once per ingest run (instead of per-reference) and pass it
  down through the ingest pipeline.
- Added unit coverage to lock down the OpenAlex config behavior.

## Related

- `src/erdos/core/ingest/fetch.py`
- `src/erdos/core/clients/openalex.py` (`OpenAlexConfig`)
