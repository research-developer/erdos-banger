# Friction Report: CLI Maximization Test (2026-01-26)

**Purpose:** Test all CLI capabilities for Problem #848 (Erdős-Sárközy)
**Status:** Archived

## Issues Encountered

### 1. BUG-034: Exa --save-leads crashes on empty title
**Severity:** P2 (workaround exists)
**Filed:** docs/_archive/bugs/bug-034-exa-save-leads-empty-title.md
**Resolution:** Fixed (fallback title generation when Exa returns an empty title).

### 2. Semantic search requires extra dependency
**Severity:** P3 (expected behavior)
**Command:** `erdos search "density" --semantic`
**Error:** `Error: Embedding functionality requires the 'embeddings' extra. Install with: uv sync --extra embeddings`
**Resolution:** This is documented behavior, not a bug. User needs to install embeddings extra.

### 3. `--status decidable` not supported
**Severity:** P3 (documentation gap)
**Command:** `erdos list --tag "number theory" --status decidable`
**Resolution:** Status filtering now accepts `decidable`. Note: the dataset still needs to reflect "decidable" for #848 if it is currently marked `unknown`.

### 4. Lean toolchain not installed
**Severity:** N/A (environment-specific)
**Command:** `erdos lean init`
**Error:** `Error: 'lake' executable not found on PATH`
**Resolution:** Install Lean toolchain via elan. (On this machine, elan has since been installed.)

### 5. Environment variables not auto-loaded from .env
**Severity:** P3 (documentation improvement)
**Commands:** `erdos research exa search`, `erdos ask`
**Issue:** API keys in `.env` file not automatically loaded; need explicit `source .env` or `export`
**Resolution:** CLI now auto-loads `.env` by default (disable with `ERDOS_LOAD_DOTENV=0`). See `docs/developer/configuration.md`.

## Summary

| Issue | Severity | Status |
|-------|----------|--------|
| BUG-034 Exa empty title | P2 | Fixed |
| Semantic search extra | P3 | Expected (documented) |
| Status decidable filter | P3 | Fixed |
| Lean not installed | N/A | Environment setup (resolved locally) |
| .env not auto-loaded | P3 | Fixed |

## Successful Operations

All core CLI functionality worked correctly:
- `erdos sync submodule` ✓
- `erdos sync website 848` ✓
- `erdos show 848` ✓
- `erdos research init/status/lead/hypothesis/task/note/synthesize` ✓
- `erdos ingest 848` ✓
- `erdos refs problem/zbmath` ✓
- `erdos search --build-index` ✓
- `erdos research exa search` ✓ (without --save-leads)
- `erdos ask 848` ✓ (with explicit env export)
- `erdos dashboard` ✓
- `erdos research fmt/validate` ✓
