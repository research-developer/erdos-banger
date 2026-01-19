# Technical Debt Decks

This directory contains technical-debt writeups: spec drift, missing fixtures, incomplete implementations, or refactors that improve long-term maintainability.

## Debt Priority Definitions

| Priority | Definition |
|----------|------------|
| **P0** | Immediate risk (security/data loss) if not addressed |
| **P1** | Blocks planned work or causes frequent breakage |
| **P2** | Material quality gap; should be scheduled soon |
| **P3** | Minor; clean up when touching nearby code |
| **P4** | Enhancement / polish |

## Active Debt

*No active debt items.*

## Archived Debt

All debt below has been resolved and archived to `docs/_archive/debt/`.

| ID | Title | Priority | Status | Commit |
|----|-------|----------|--------|--------|
| DEBT-001 | Spec 005 drift/inconsistency | P1 | Fixed | 19f2225 |
| DEBT-002 | Spec 006 search CLI drift | P2 | Fixed | bd21e6c |
| DEBT-003 | Spec 008 fixtures incomplete | P1 | Fixed | bfb5b70 |
| DEBT-004 | Lean scaffolding absent vs Spec 007 | P1 | Fixed | 7e17d21 |
| DEBT-005 | Placeholder tests vs "real" coverage | P2 | Fixed | 59bdeac |
| DEBT-006 | Ephemeral test data / persistence gaps | P1 | Fixed | a47d9f2,57cf739 |
| DEBT-007 | Lean compilation not enforced in CI | P1 | Fixed | c9cbf24,ec0b93d |
| DEBT-008 | Unused fixtures / no golden tests | P2 | Fixed | 57cf739 |
| DEBT-009 | Upstream data not integrated | P1 | Fixed | 70ae1ab,96eb024 |
| DEBT-010 | No smoke test | P2 | Fixed | 70ae1ab,c9cbf24 |
| DEBT-013 | Spec 010 scope planning | P1 | Fixed | 931b98b |
| DEBT-011 | SPEC-020 status clarification | P2 | Resolved | c526e10 |
| DEBT-012 | Broad exception handling in ingest.py | P1 | Fixed | 2cb6fac |
| DEBT-014 | Roadmap/tracking docs drift after v1.1 | P2 | Fixed | c526e10 |

**Next Debt ID:** DEBT-015

### Archived Debt Decks

- `docs/_archive/debt/debt-001-spec-005-ssot-drift.md`
- `docs/_archive/debt/debt-013-spec-010-scope.md`
- `docs/_archive/debt/debt-011-spec-020-not-implemented.md`
- `docs/_archive/debt/debt-012-broad-exception-handling.md`
- `docs/_archive/debt/debt-014-roadmap-and-tracking-docs-drift.md`
- `docs/_archive/debt/debt-002-spec-006-search-cli-drift.md`
- `docs/_archive/debt/debt-003-spec-008-fixtures-incomplete.md`
- `docs/_archive/debt/debt-004-lean-scaffolding-missing.md`
- `docs/_archive/debt/debt-005-placeholder-tests.md`
- `docs/_archive/debt/debt-006-ephemeral-test-data.md`
- `docs/_archive/debt/debt-007-lean-ci-never-runs.md`
- `docs/_archive/debt/debt-008-unused-golden-fixtures.md`
- `docs/_archive/debt/debt-009-upstream-data-not-integrated.md`
- `docs/_archive/debt/debt-010-no-smoke-test.md`
