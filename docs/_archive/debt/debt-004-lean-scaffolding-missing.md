# Debt: Lean Scaffolding Absent vs Spec 007

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-17
**Fixed:** 2026-01-17
**Commit:** 7e17d21

## Summary

Spec 007 defines a fully pinned Lean project and runner implementation, but the repository currently contains only empty directories under `formal/lean/` and stub implementations in Python.

## Current State

- `formal/lean/` contains no `lean-toolchain`, `lakefile.lean`, or root modules.
- `src/erdos/core/lean_runner.py` and `src/erdos/core/formalizer.py` are stubs raising `NotImplementedError`.
- CI caches `formal/lean/.lake` keyed by hashes of `formal/lean/lean-toolchain` and `formal/lean/lakefile.lean`, which are currently absent.

## Impact

- Lean-dependent behavior is not implementable/testable yet.
- CI caching keys may be less meaningful until the Lean project files exist.

## Recommendation

Implement Spec 007 (or a clearly scoped subset) as the next major milestone:
- Add the minimal Lean project files under `formal/lean/`
- Implement `LeanRunner` (subprocess + parsing) and `generate_skeleton`
- Add/enable Lean-dependent tests and fixtures (Spec 008)

## Related

- `docs/_archive/specs/spec-007-lean-integration.md`
- `formal/lean/`
- `src/erdos/core/lean_runner.py`
- `src/erdos/core/formalizer.py`
- `.github/workflows/ci.yml`
