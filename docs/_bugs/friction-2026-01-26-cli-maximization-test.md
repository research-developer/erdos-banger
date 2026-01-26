# Friction Report: CLI Maximization Test (2026-01-26)

**Purpose:** Test all CLI capabilities for Problem #848 (Erdős-Sárközy)

## Issues Encountered

### 1. BUG-034: Exa --save-leads crashes on empty title
**Severity:** P2 (workaround exists)
**Filed:** docs/_bugs/bug-034-exa-save-leads-empty-title.md

### 2. Semantic search requires extra dependency
**Severity:** P3 (expected behavior)
**Command:** `erdos search "density" --semantic`
**Error:** `Error: Embedding functionality requires the 'embeddings' extra. Install with: uv sync --extra embeddings`
**Resolution:** This is documented behavior, not a bug. User needs to install embeddings extra.

### 3. `--status decidable` not supported
**Severity:** P3 (documentation gap)
**Command:** `erdos list --tag "number theory" --status decidable`
**Error:** `Error: Invalid status 'decidable'. Valid values: disproved, open, partially_solved, proved`
**Note:** Upstream data has "decidable" as a status, but CLI doesn't support filtering by it. The enriched YAML shows status as "unknown" for problem 848 (should be "decidable").

### 4. Lean toolchain not installed
**Severity:** N/A (environment-specific)
**Command:** `erdos lean init`
**Error:** `Error: 'lake' executable not found on PATH`
**Resolution:** User needs to install Lean toolchain via elan. Not a CLI bug.

### 5. Environment variables not auto-loaded from .env
**Severity:** P3 (documentation improvement)
**Commands:** `erdos research exa search`, `erdos ask`
**Issue:** API keys in `.env` file not automatically loaded; need explicit `source .env` or `export`
**Note:** This is likely expected behavior (CLI doesn't auto-load .env), but could be documented more clearly in the skill.

## Summary

| Issue | Severity | Status |
|-------|----------|--------|
| BUG-034 Exa empty title | P2 | Bug filed |
| Semantic search extra | P3 | Expected (documented) |
| Status decidable filter | P3 | Enhancement request |
| Lean not installed | N/A | Environment setup |
| .env not auto-loaded | P3 | Documentation |

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
