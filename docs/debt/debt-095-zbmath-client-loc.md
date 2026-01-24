# DEBT-095: zbMATH Client Module LOC Violation

**Priority:** P4 (Enhancement)
**Status:** Exempted
**Found:** 2026-01-24
**Exempted:** 2026-01-24

## Description

The zbMATH Open API client (SPEC-031/1) exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/clients/zbmath.py` | 792 | 500 | +292 |

## Justification for Exemption

This module contains a complete HTTP client with 6 bounded responsibilities:

1. **Configuration** — `ZbMathConfig` dataclass with environment integration
2. **Data models** — `MSCCode`, `ZbMathEntry` with JSON serialization
3. **API response parsing** — Extracting title, authors, year, links, MSC codes, reviews
4. **HTTP client** — Rate limiting (2s delay), retry with exponential backoff
5. **Caching** — SHA256-keyed file cache with 30-day TTL
6. **Search methods** — DOI lookup, zbMATH ID lookup, MSC search, title search

The module is cohesive: all types and functions support a single capability (zbMATH API integration).
The zbMATH API has complex response structures requiring substantial parsing logic.

## Resolution

Exempted via inline marker:
- `zbmath.py`: Line 3 `# exempt: DEBT-095`

## Future Refactoring Opportunities

If the module grows further:
1. Extract response parsing to `zbmath_parser.py`
2. Extract caching logic to a reusable `clients/cache.py` module
3. Consider splitting into `zbmath_client.py` (HTTP) and `zbmath_models.py` (data)

Currently, the cohesion benefit outweighs the LOC cost.
