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

| ID | Title | Priority | Status | Affects |
|----|-------|----------|--------|---------|
| DEBT-006 | [Ephemeral Test Data](debt-006-ephemeral-test-data.md) | P1 | Open | Search index, CLI, data workflow |
| DEBT-007 | [Lean CI Never Runs](debt-007-lean-ci-never-runs.md) | P1 | Open | Lean integration, CI pipeline |
| DEBT-008 | [Unused Golden Fixtures](debt-008-unused-golden-fixtures.md) | P2 | Open | Test coverage, regression detection |
| DEBT-009 | [Upstream Data Not Integrated](debt-009-upstream-data-not-integrated.md) | P1 | Open | Data loading, schema validation |
| DEBT-010 | [No Smoke Test](debt-010-no-smoke-test.md) | P2 | Open | Developer onboarding, quick validation |

## Archived Debt

All debt below has been resolved and archived to `docs/_archive/debt/`.

| ID | Title | Priority | Status | Commit |
|----|-------|----------|--------|--------|
| DEBT-001 | Spec 005 drift/inconsistency | P1 | Fixed | 19f2225 |
| DEBT-002 | Spec 006 search CLI drift | P2 | Fixed | bd21e6c |
| DEBT-003 | Spec 008 fixtures incomplete | P1 | Fixed | bfb5b70 |
| DEBT-004 | Lean scaffolding absent vs Spec 007 | P1 | Fixed | 7e17d21 |
| DEBT-005 | Placeholder tests vs "real" coverage | P2 | Fixed | 59bdeac |

**Next Debt ID:** DEBT-011

### Archived Debt Decks

- `docs/_archive/debt/debt-001-spec-005-ssot-drift.md`
- `docs/_archive/debt/debt-002-spec-006-search-cli-drift.md`
- `docs/_archive/debt/debt-003-spec-008-fixtures-incomplete.md`
- `docs/_archive/debt/debt-004-lean-scaffolding-missing.md`
- `docs/_archive/debt/debt-005-placeholder-tests.md`
