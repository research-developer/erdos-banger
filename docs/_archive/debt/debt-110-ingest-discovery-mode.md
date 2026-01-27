# DEBT-110: Add Paper Discovery Mode to Ingest

**Created:** 2026-01-26
**Priority:** P2 (downgraded - Phase 1 complete)
**Status:** Superseded by SPEC-036
**Tracks:** BUG-039

## Resolution

Phase 1 (manual add) is complete. Phases 2-3 (automatic discovery/enrichment) are **new feature work**, not debt. They are fully specified in:

**→ See `docs/_specs/spec-036-lead-enrichment-pipeline.md`**

SPEC-036 provides:
- Complete CLI interface (`erdos research lead enrich`, `erdos research lead ingest`)
- Data model changes (LeadRecord extensions, ManifestEntry source tracking)
- Implementation design (services, bridges, deduplication)
- Test cases (unit, integration, acceptance)
- Error handling matrix

## Phase 1: Manual Add ✅ COMPLETE

```bash
# Add specific paper by arXiv ID
erdos refs add 848 --arxiv 2511.16072

# Ingest fetches metadata + downloads source
erdos ingest 848 --force
```

**Commit:** `f9b8441`

## Phases 2-3: Covered by SPEC-036

| Phase | SPEC-036 Section | Commands |
|-------|------------------|----------|
| Phase 2: Search Integration | §2, §4.1 | `erdos research lead enrich` |
| Phase 3: Discovery Mode | §2, §4.2 | `erdos research lead ingest` |

## Acceptance Criteria

- [x] Can add arXiv:2511.16072 to Problem 848 via CLI ✅
- [ ] Can search for "squarefree products" and see relevant papers → SPEC-036
- [ ] Exa API integrated for semantic search → SPEC-036
- [ ] Discovery mode works on problems with empty references → SPEC-036

## Related

- SPEC-036: Lead Enrichment Pipeline (authoritative spec)
- Issue #34: Lead enrichment pipeline (tracks implementation)
- BUG-039: Ingest cannot discover papers (original issue)
