# DEBT-101: Lean/Mathlib Version Significantly Behind

**Status:** Open
**Priority:** P2 (Technical debt accumulating)
**Created:** 2026-01-24
**Related:** All Lean integration (SPEC-007, SPEC-016, SPEC-033)

## Problem

The project uses Lean v4.12.0 and Mathlib v4.12.0, but the latest stable versions are:

| Component | Current | Latest | Gap |
|-----------|---------|--------|-----|
| Lean 4 | v4.12.0 | v4.27.0 | 15 versions |
| Mathlib4 | v4.12.0 | v4.27.0 | 15 versions |

## Evidence

```
# formal/lean/lean-toolchain
leanprover/lean4:v4.12.0

# formal/lean/lakefile.lean
require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.12.0"
```

Latest stable Lean release: v4.27.0 (January 23, 2026)
Source: https://github.com/leanprover/lean4/releases

## Impact

1. **Security:** Missing security patches from 15 Lean releases
2. **Features:** Missing new tactic improvements, better error messages
3. **Compatibility:** Future Mathlib updates may require newer Lean
4. **Test fixtures:** Already hit deprecated `version` field issue (DEBT-099)

## Risk Assessment

**Upgrade complexity: MEDIUM-HIGH**
- Mathlib version must match Lean toolchain version
- Breaking changes in Lake (package manifest format)
- Potential API changes in Mathlib theorems we import
- CI pipeline may need updates

## Fix Plan

### Phase 1: Preparation
1. [ ] Review Lean 4 RELEASES.md for breaking changes v4.12 → v4.27
2. [ ] Review Mathlib4 changelog for API changes
3. [ ] Identify all Mathlib imports in `formal/lean/Erdos/`

### Phase 2: Upgrade (in a feature branch)
1. [ ] Update `lean-toolchain` to latest stable
2. [ ] Update `lakefile.lean` Mathlib pin
3. [ ] Run `lake update` to regenerate `lake-manifest.json`
4. [ ] Fix compilation errors in `Erdos/*.lean`
5. [ ] Run `lake build` and fix any remaining issues

### Phase 3: Verification
1. [ ] Verify `test-with-lean` CI job passes
2. [ ] Verify `erdos lean check` works
3. [ ] Verify `erdos lean formalize` works
4. [ ] Update any version-specific documentation

## Files to Update

- `formal/lean/lean-toolchain` - Lean version
- `formal/lean/lakefile.lean` - Mathlib pin
- `formal/lean/lake-manifest.json` - Auto-regenerated
- `tests/fixtures/sync/proof_repo/*/lean-toolchain` - Test fixtures (if needed)
- `docs/_vendor-docs/lean/` - Any version-specific docs

## Acceptance Criteria

1. [ ] Lean toolchain upgraded to v4.27.0 (or latest at time of fix)
2. [ ] Mathlib4 upgraded to matching version
3. [ ] All `formal/lean/Erdos/*.lean` files compile
4. [ ] `test-with-lean` CI job passes
5. [ ] No regressions in Lean-dependent CLI commands

## Effort Estimate

4-8 hours (depending on breaking changes encountered)

## References

- [Lean 4 Releases](https://github.com/leanprover/lean4/releases)
- [Mathlib4 Releases](https://github.com/leanprover-community/mathlib4/releases)
- [Lake Documentation](https://github.com/leanprover/lean4/tree/master/src/lake)
