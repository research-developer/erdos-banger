# DEBT-110: Add Paper Discovery Mode to Ingest

**Created:** 2026-01-26
**Priority:** P1
**Tracks:** BUG-039

## Problem

The research workflow is broken for problems with incomplete reference metadata. There's no way to discover and ingest relevant papers without manual intervention.

## Current State

```
erdos ingest <id>  →  Only fetches pre-defined references
erdos refs problem <id>  →  Shows references (often incomplete)
```

No search/discovery capability.

## Desired State

```bash
# Add specific paper by arXiv ID
erdos refs add 848 --arxiv 2511.16072

# Search and discover related papers
erdos ingest 848 --discover  # Uses problem statement + Exa/OpenAlex
erdos ingest 848 --search "squarefree products Erdos"

# Import from bibliography
erdos refs import 848 --bibtex refs.bib
```

## Implementation Sketch

### Phase 1: Manual Add (Quick Win)
1. Add `erdos refs add <id> --arxiv <arxiv_id>` command
2. Fetches metadata from arXiv API
3. Appends to `literature/manifests/<id>.yaml`
4. Downloads source tarball to `literature/cache/`

### Phase 2: Search Integration
1. Add Exa integration for semantic paper search
2. Use problem statement as initial query
3. Filter by math.NT, math.CO categories
4. Present candidates for user selection

### Phase 3: Discovery Mode
1. `--discover` flag extracts keywords from problem statement
2. Searches multiple sources (arXiv, Semantic Scholar, zbMATH)
3. Deduplicates and ranks by relevance
4. Auto-adds high-confidence matches, prompts for others

## Acceptance Criteria

- [ ] Can add arXiv:2511.16072 to Problem 848 via CLI
- [ ] Can search for "squarefree products" and see relevant papers
- [ ] Exa API integrated for semantic search
- [ ] Discovery mode works on problems with empty references

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
