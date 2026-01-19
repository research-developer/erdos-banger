# Technical Debt 011: SPEC-020 (OpenAlex) Status Mismatch

**Date:** 2026-01-19
**Status:** Resolved
**Priority:** P2
**Impact:** Documentation clarity
**Resolved:** 2026-01-19
**Commit:** (pending)

## Problem

This deck was created during a v1.1 post-completion review as a caution that SPEC-020 was
marked **Ready** while not yet implemented.

After review, this is **not** a mismatch:

- **Ready** means "fully specified and implementable" (not "already implemented").
- SPEC-020 targets **v1.2+**, while SPEC-010 targets **v1.1**; the intent is a future
  augmentation/refactor of ingestion metadata sources.

## Spec Conflict

| Aspect | SPEC-010 (Implemented) | SPEC-020 (Not Started) |
|--------|------------------------|------------------------|
| Primary Source | Crossref (DOI) | OpenAlex |
| Target Version | v1.1 | v1.2+ |
| Status | Implemented | "Ready" (misleading) |

## Evidence

SPEC-020 Section 0 (Executive Summary):
> "Recommendation: Use OpenAlex as PRIMARY source, with arXiv API as fallback"

SPEC-020 Section 5 (Integration with Ingest Command):
> Shows updated flow that would require refactoring `ingest.py`

But `ingest.py` currently:
- Uses Crossref for DOI metadata
- Uses arXiv for arXiv IDs
- No OpenAlex integration

## Resolution Options

1. **(A) Implement in v1.1** - Major scope creep, breaks existing SPEC-010 work
2. **(B) Defer to v1.2+** - Update SPEC-020 status from "Ready" to "Deferred"
3. **(C) Make Optional** - Keep Crossref primary in v1.1, add OpenAlex as `--source openalex` option in v1.2

**Resolution:** Keep SPEC-020 as a v1.2+ spec (Ready) and treat the provider choice
(OpenAlex primary vs augment) as a future design/implementation decision, not a v1.1 defect.

## Action Items

- [ ] Update SPEC-020 status from "Ready" to "Deferred (v1.2+)"
- [ ] Update SPEC-020 to clarify it augments (not replaces) SPEC-010
- [ ] Add SPEC-020 to PROGRESS.md as "Phase 3" or similar
- [ ] Document migration path from Crossref→OpenAlex

## References

- SPEC-010: `docs/specs/spec-010-ingest-command.md`
- SPEC-020: `docs/specs/spec-020-openalex-integration.md`
- PROGRESS.md: `PROGRESS.md`
