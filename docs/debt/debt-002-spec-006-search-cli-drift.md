# Debt: Spec 006 Search CLI Drift

**Priority:** P2
**Status:** Open
**Found:** 2026-01-17

## Summary

`docs/specs/spec-006-search-index.md` does not fully describe current `erdos search` behavior.

## Drift Items

- Implementation supports `--build-index` on `erdos search`, but Spec 006 CLI section omits it.
- Implementation enriches results with problem titles (best-effort) and includes extra fields (`title`, `reference_doi`, `use_fts`) not shown in the spec snippet.
- JSON correctness requirements for `--json` + `--build-index` should be explicit in the spec.

## Impact

- Specs are SSOT for other agents; drift increases the chance of regressions or duplicated feature work.

## Recommendation

Either:
- Update Spec 006 CLI Integration to match current command flags and output schema, or
- Remove/rework the implementation to match the spec if the spec is the intended contract.

## Related

- `docs/specs/spec-006-search-index.md`
- `src/erdos/commands/search.py`

