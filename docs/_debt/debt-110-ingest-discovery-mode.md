# DEBT-110: Add Paper Discovery Mode to Ingest

**Created:** 2026-01-26
**Priority:** P2 (downgraded - Phase 1 complete, remaining is feature work)
**Tracks:** BUG-039

## Problem

The research workflow was broken for problems with incomplete reference metadata. Phase 1 (manual add) is now complete. Phases 2-3 (automatic discovery) remain as feature work.

## Current State (Phase 1 Complete)

```bash
# ✅ WORKS - Add specific paper by arXiv ID
erdos refs add 848 --arxiv 2511.16072

# ✅ WORKS - Ingest fetches metadata + downloads source
erdos ingest 848 --force

# ❌ NOT IMPLEMENTED - Automatic discovery
erdos ingest 848 --discover
erdos ingest 848 --search "squarefree products Erdos"
```

## Desired State (Phases 2-3)

```bash
# Search and discover related papers (Phase 2)
erdos ingest 848 --discover  # Uses problem statement + Exa/OpenAlex
erdos ingest 848 --search "squarefree products Erdos"

# Import from bibliography (Phase 3)
erdos refs import 848 --bibtex refs.bib
```

## Implementation Status

### Phase 1: Manual Add ✅ COMPLETE
1. ✅ `erdos refs add <id> --arxiv <arxiv_id>` command exists
2. ✅ Updates `data/problems_enriched.yaml` with new reference
3. ✅ `erdos ingest` fetches metadata via FallbackProvider
4. ✅ Downloads arXiv source tarball to `literature/cache/arxiv/`

**Commit:** `f9b8441` (erdos refs add)

### Phase 2: Search Integration (NOT STARTED)
1. Add Exa integration for semantic paper search
2. Use problem statement as initial query
3. Filter by math.NT, math.CO categories
4. Present candidates for user selection

### Phase 3: Discovery Mode (NOT STARTED)
1. `--discover` flag extracts keywords from problem statement
2. Searches multiple sources (arXiv, Semantic Scholar, zbMATH)
3. Deduplicates and ranks by relevance
4. Auto-adds high-confidence matches, prompts for others

## Acceptance Criteria

- [x] Can add arXiv:2511.16072 to Problem 848 via CLI ✅
- [ ] Can search for "squarefree products" and see relevant papers (Phase 2)
- [ ] Exa API integrated for semantic search (Phase 2)
- [ ] Discovery mode works on problems with empty references (Phase 3)

## Dependencies

- Exa API key (already in .env: `EXA_API_KEY`)
- arXiv API client (already exists: `erdos.core.clients.arxiv`)
- Manifest writer (already exists: `erdos.core.ingest`)

## Effort

- Phase 1: ~2-4 hours
- Phase 2: ~4-8 hours
- Phase 3: ~8-16 hours

## Notes

This is a significant gap that makes the "research" part of the research toolkit non-functional for many problems. Should be prioritized.
