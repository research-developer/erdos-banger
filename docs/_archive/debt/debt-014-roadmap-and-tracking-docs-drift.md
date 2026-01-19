# Technical Debt 014: Roadmap/Tracking Docs Drift After v1.1 Completion

**Date:** 2026-01-19
**Status:** Fixed
**Priority:** P2
**Impact:** Contributor confusion, incorrect SSOT pointers
**Fixed:** 2026-01-19
**Commit:** c526e10

## Problem

After v1.1 landed, several documentation “index” files still reflected pre-v1.1 state:

- `docs/specs/README.md` still marked **v1.1 (PENDING)** and SPEC-010/011 as **Pending**.
- `README.md` still marked SPEC-010/011 as **Pending**.
- `docs/INDEX.md` “Next ID” counters were stale vs the category SSOT files.
- `docs/bugs/README.md` and `docs/debt/README.md` had “(pending commit)” placeholders while fixes had already landed.
- Several archived bug/debt decks still had `Status: Open` despite being fixed/resolved.

## Fix

- Updated spec/roadmap docs to reflect **v1.1 DONE** and SPEC-010/011 as **Complete**.
- Updated `docs/INDEX.md` to match the SSOT “Next ID” counters in the category READMEs.
- Reconciled bug/debt tracking:
  - Filled in commit hashes for already-fixed items (e.g., BUG-007/008).
  - Ensured archived decks reflect fixed/resolved status.
  - Normalized DEBT numbering where an archived deck had a duplicate ID.

## Related

- `docs/specs/README.md`
- `README.md`
- `docs/INDEX.md`
- `docs/bugs/README.md`
- `docs/debt/README.md`
