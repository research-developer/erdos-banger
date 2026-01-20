# Technical Debt 018: DRY Violations (Code Duplication)

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** b069060, 786cd42, ff4e412, 3dd1610, fbdd5a0
**Priority:** P1 (Blocks planned work or causes frequent breakage)
**Impact:** Maintainability, consistency, bug propagation

## Summary

Several cross-cutting patterns were duplicated across commands/core logic (timing, JSON-mode setup, dependency bootstrap, stable keys, arXiv download/extract). This created drift risk: fixes would land in one copy but not the others.

## Resolution

Duplication was removed by centralizing each “knowledge unit” in one place:

- **Timing**: `src/erdos/core/timing.py:measure_time_ms()` (`ff4e412`)
- **Command JSON-mode setup**: `src/erdos/commands/presenter.py:set_json_mode()` (`fbdd5a0`)
- **Dependency bootstrap + error translation**: `src/erdos/core/context.py` + `src/erdos/commands/app_context.py` (`3dd1610`)
- **Stable reference keys**: `src/erdos/core/ingest.py:get_stable_key()` (`786cd42`)
- **arXiv download/extract logic**: `src/erdos/core/ingest.py:_download_and_extract_arxiv()` (`b069060`)

## Verification

```bash
# JSON setup is no longer duplicated across command modules
rg -n "ctx\\.ensure_object\\(dict\\)" src/erdos/commands

# Stable key function exists in exactly one place
rg -n "def get_stable_key\\(" -S src/erdos/core/ingest.py

# arXiv download/extract helper exists (single implementation)
rg -n "def _download_and_extract_arxiv\\(" -S src/erdos/core/ingest.py

# Timing helper used across commands
rg -n "measure_time_ms\\(" src/erdos/commands

# Quality gates
make ci
```

## Acceptance Criteria

- [x] Loader bootstrap/error translation consolidated
- [x] Time measurement consolidated
- [x] JSON setup consolidated
- [x] arXiv download logic exists in exactly one place
- [x] Stable key function exists in exactly one place
- [x] All tests pass (`make ci`)

## References

- Robert C. Martin, "Clean Code" Chapter 17: Smells and Heuristics — "Duplication"
