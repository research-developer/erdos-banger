# DEBT-093: Exa Client Module LOC Violation

**Priority:** P4 (Enhancement)
**Status:** Exempted
**Found:** 2026-01-24
**Exempted:** 2026-01-24

## Description

The Exa Research API client (SPEC-029/1) exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/clients/exa.py` | 541 | 500 | +41 |

## Justification for Exemption

This module contains a complete HTTP client with 5 bounded responsibilities:

1. **Configuration** — `ExaConfig` dataclass with environment integration
2. **Data models** — `ExaSource` and `ExaResearchResult` with JSON serialization
3. **URL parsing** — arXiv ID and DOI extraction from result URLs
4. **HTTP client** — Rate limiting, retry with exponential backoff
5. **Caching** — SHA256-keyed file cache with TTL expiry

The module is cohesive: all types and functions support a single capability (Exa API integration).
The marginal violation (+41 LOC) doesn't justify splitting into multiple modules.

## Resolution

Exempted via inline marker near the top of the file:
- `src/erdos/core/clients/exa.py`: `# exempt: DEBT-093`

## Future Refactoring Opportunities

If the module grows further:
1. Extract URL parsing helpers to `clients/url_utils.py`
2. Extract caching logic to a reusable `clients/cache.py` module
3. Consider using `attrs` or `msgspec` for more compact model definitions

Currently, the cohesion benefit outweighs the LOC cost.
