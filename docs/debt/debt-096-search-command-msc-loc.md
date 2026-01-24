# DEBT-096: Search Command Module LOC Violation

**Priority:** P4 (Enhancement)
**Status:** Exempted
**Found:** 2026-01-24
**Exempted:** 2026-01-24

## Description

The search command module (SPEC-031/3 MSC integration) exceeds the LOC threshold:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/commands/search.py` | 519 | 400 | +119 |

## Justification for Exemption

This module supports multiple search modes with shared CLI infrastructure:

1. **BM25 search** — Local FTS5 index search
2. **Semantic search** — Vector-based similarity search
3. **Hybrid search** — Combined BM25 + semantic scoring
4. **MSC search** — zbMATH API search by Mathematics Subject Classification (SPEC-031)

Each mode shares:
- CLI flag parsing and validation
- Output formatting (JSON + human)
- Error handling and exit codes

The MSC search mode (+~100 LOC) was added for SPEC-031/3 to enable `erdos search --msc "11B05"` without requiring a separate command.

## Resolution

Exempted via inline marker near the top of the file:
- `src/erdos/commands/search.py`: `# exempt: DEBT-096`

## Future Refactoring Opportunities

If the module grows further:
1. Extract MSC search logic to a dedicated `search_msc.py` submodule
2. Extract output formatters to `search_output.py`
3. Consider a strategy pattern for search mode dispatch

Currently, keeping all search modes together improves discoverability and reduces import complexity.
