# Technical Debt 013: SPEC-010 Exceeds Single-Iteration Scope

**Date:** 2026-01-19
**Status:** Fixed
**Impact:** Previously blocked v1.1 progress
**Fixed:** 2026-01-19
**Commit:** 931b98b

## Problem

SPEC-010 (Ingest Command) is currently specified as a single task in PROGRESS.md, but exceeds the Ralph Wiggum protocol's single-iteration scope limits:

**Protocol Stop Condition #4:**
> A change would touch >10 files or exceed ~500 LoC for a single task.

**SPEC-010 Actual Scope:**
- Source modules: 5+ files (literature_paths, arxiv_client, crossref_client, ingest, commands/ingest)
- Test modules: 6+ files (unit tests for each module + integration tests)
- Fixture files: arXiv/Crossref response samples
- Total estimated LoC: ~800-1000
- Total files touched: 12-15

## Evidence

Attempted implementation in iteration 2026-01-19:
- Created `literature_paths.py` with tests (passing)
- Found partial `arxiv_client.py` in untracked files
- Discovered extensive remaining work:
  - crossref_client.py (not started)
  - ingest.py core logic (not started)
  - commands/ingest.py (not started)
  - Integration tests (not started)
  - Fixture files (not started)

## Recommendation

Break SPEC-010 into smaller, atomic tasks:

1. **SPEC-010-A**: Literature path conventions (`literature_paths.py` + tests)
2. **SPEC-010-B**: arXiv client (`arxiv_client.py` + unit tests + fixtures)
3. **SPEC-010-C**: Crossref client (`crossref_client.py` + unit tests + fixtures)
4. **SPEC-010-D**: Ingest core logic (`ingest.py` + unit tests)
5. **SPEC-010-E**: Ingest command (`commands/ingest.py` + integration tests)

Each subtask is independently testable and stays within iteration limits.

## References

- SPEC-010: `docs/specs/spec-010-ingest-command.md`
- Protocol: `docs/_ralphwiggum/protocol.md`
- PROGRESS.md: Current task tracking
