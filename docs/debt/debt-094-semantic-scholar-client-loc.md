# DEBT-094: Semantic Scholar Client Module LOC Violation

**Priority:** P4 (Enhancement)
**Status:** Exempted
**Found:** 2026-01-24
**Exempted:** 2026-01-24

## Description

The Semantic Scholar API client (SPEC-030/1) exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/clients/semantic_scholar.py` | 684 | 500 | +184 |

## Justification for Exemption

This module contains a complete HTTP client with 6 bounded responsibilities:

1. **Configuration** — `S2Config` dataclass with environment integration
2. **Data models** — `S2Paper`, `CitationContext`, `S2Reference` with JSON serialization
3. **Identifier normalization** — DOI, arXiv ID, S2 ID detection and API formatting
4. **HTTP client** — Rate limiting, retry with exponential backoff
5. **Caching** — SHA256-keyed file cache with TTL expiry
6. **3 API endpoints** — `get_paper()`, `get_citations()`, `get_references()`

The module is cohesive: all types and functions support a single capability (Semantic Scholar API integration). The extra LOC compared to Exa is due to:
- 3 data models instead of 2 (citations have separate structure from references)
- 3 API methods instead of 1 (papers, citations, references)
- More robust identifier normalization (DOI, arXiv legacy/modern, S2 IDs)

## Resolution

Exempted via inline marker:
- `semantic_scholar.py`: Line 3 `# exempt: DEBT-094`

## Future Refactoring Opportunities

If the module grows further:
1. Extract shared caching logic to `clients/cache.py` (reusable with Exa)
2. Extract retry/rate-limiting to `clients/http_utils.py`
3. Consider using `attrs` or `msgspec` for more compact model definitions

Currently, the cohesion benefit outweighs the LOC cost.
