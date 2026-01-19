# Bug 007: Missing `requests` Dependency in pyproject.toml

**Priority:** P0 (Critical)
**Status:** Open
**Found:** 2026-01-19
**Fixed:** —
**Commit:** —

## Description

The `requests` library is imported in three core modules but is not listed in `[project.dependencies]` in pyproject.toml. Installation will fail for users.

## Files Affected

- `src/erdos/core/ingest.py` - imports `requests`
- `src/erdos/core/arxiv_client.py` - imports `requests`
- `src/erdos/core/crossref_client.py` - imports `requests`
- `pyproject.toml` - missing `requests>=2.32.5`

## Steps to Reproduce

```bash
# Fresh install
uv sync
uv run erdos ingest 6
# ModuleNotFoundError: No module named 'requests'
```

## Expected Behavior

Package installs successfully with all dependencies.

## Actual Behavior

Installation succeeds but runtime fails because `requests` is not installed.

## Root Cause

SPEC-010 Section 5.0 explicitly requires `requests>=2.32.5` but the dependency was never added to pyproject.toml. Only `types-requests` (dev dependency) was added.

## Fix

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "requests>=2.32.5",  # Required for ingest/arxiv/crossref clients
    # ... existing deps
]
```

## Related

- SPEC-010: `docs/specs/spec-010-ingest-command.md`
- SPEC-020: `docs/specs/spec-020-openalex-integration.md` (also needs requests)
