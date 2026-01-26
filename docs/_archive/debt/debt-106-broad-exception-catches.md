# DEBT-106: Broad Exception Catches Without Justification

**Priority:** P3
**Status:** Fixed (documentation + boundary clarity)
**Found:** 2026-01-24
**Fixed:** 2026-01-25
**Found Commit:** 2082df5
**Fix Commit:** 0200a99

## Summary

A number of `except Exception` catches are intentional at CLI boundaries, optional-dependency probing, and best-effort operations. The debt was that several broad catches did not explain why they were broad, making future audits low-signal.

## Resolution

- Added explicit justification comments to every `except Exception` / `except Exception as e` clause that remains broad.
- Kept broad catches only at deliberate boundaries (CLI commands, best-effort background tasks, optional imports). Where practical, existing code narrows exceptions to concrete types.

Note: the repo's default Ruff configuration does not enable `BLE001`, and `warn_unused_ignores = true` means adding `# noqa: BLE001` without enabling the rule would fail CI. We prefer explicit comments over unused `noqa`s.

## Verification

- `rg -n 'except Exception(?: as [A-Za-z_][A-Za-z0-9_]*)?:\s*$' src/erdos` returns no matches (production code only; every broad catch has an inline rationale).
- `make ci`

## Acceptance Criteria

- [x] All broad `except Exception` clauses include a rationale
- [x] No unused `# noqa` suppressions introduced
- [x] `make ci` passes
