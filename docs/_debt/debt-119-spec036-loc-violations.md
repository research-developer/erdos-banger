# DEBT-119: SPEC-036 LOC Violations

**Priority:** P3
**Status:** Exempted
**Created:** 2026-01-29
**Component:** `src/erdos/commands/research/lead.py`, `src/erdos/core/research/store_fs.py`

## Description

Two modules exceed LOC thresholds due to SPEC-036 lead enrichment pipeline implementation:

| Module | Actual | Limit | Over |
|--------|--------|-------|------|
| `lead.py` | 520 | 400 | +120 |
| `store_fs.py` | 503 | 500 | +3 |

## Justification for Exemption

1. **`lead.py`**: Contains `add`, `list`, `show`, `update`, `enrich`, and `ingest` commands for a cohesive lead management workflow. Splitting would fragment related functionality.

2. **`store_fs.py`**: The `lead_update` method grew to support 11 enrichment/ingest fields per SPEC-036. The method is already marked with `noqa: PLR0912` for complexity.

## Mitigation

- Added `# exempt: DEBT-119` marker to both files
- If either module continues to grow, split into submodules:
  - `lead.py` → `lead_crud.py` + `lead_enrichment.py`
  - `store_fs.py` → `store_fs.py` + `store_fs_enrichment.py`

## Acceptance Criteria

- [x] Exemption markers added to both files
- [x] LOC thresholds documented
- [ ] Refactor if either module exceeds 600 LOC (future)

## Related

- SPEC-036: Lead Enrichment Pipeline
- CodeRabbit PR #43 review
