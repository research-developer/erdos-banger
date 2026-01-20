# Technical Debt 019: Dependency Inversion Principle Violations

**Date:** 2026-01-19
**Status:** Fixed
**Fixed In:** 3dd1610
**Priority:** P2 (Material quality gap; should be scheduled soon)
**Impact:** Testability, flexibility, coupling

## Summary

Commands and core logic previously constructed concrete dependencies inline (e.g., `ProblemLoader.from_default()`, `SearchIndex.from_default()`), which tightly coupled high-level code to low-level implementations and made tests rely on global state (env vars, filesystem, CWD).

## Resolution

Implemented explicit dependency inversion via ports + a small composition root:

- Ports (abstractions): `src/erdos/core/ports.py`
  - `ProblemRepository` (problem access)
  - `SearchIndexProtocol` (search/index access)
- Composition root: `src/erdos/core/context.py` (`AppContext.from_environment()`)
- CLI integration: `src/erdos/commands/app_context.py` (`get_app_context()`)
- Core logic now receives dependencies via parameters (no implicit defaults):
  - `src/erdos/core/ask.py:ask_question(..., repo=..., index=...)`
  - `src/erdos/core/ingest.py:ingest_problem_references(..., repo=...)`
  - `src/erdos/core/index_builder.py:build_index(*, loader=..., index=...)`

## Verification (First Principles)

These checks should return no matches:

```bash
# Commands should not construct dependencies directly
rg -n "ProblemLoader\\.from_default\\(|SearchIndex\\.from_default\\(" src/erdos/commands

# Core orchestration should not call from_default()
rg -n "from_default\\(" src/erdos/core/ask.py src/erdos/core/ingest.py src/erdos/core/index_builder.py
```

## Acceptance Criteria

- [x] Commands do not call `from_default()` factories directly
- [x] Core orchestration does not call `from_default()` factories directly
- [x] Abstractions exist for problem/index access (`ports.py`)
- [x] A single wiring point exists (`AppContext` + `get_app_context`)
- [x] All tests pass (`make ci`)

## References

- Robert C. Martin, SOLID: Dependency Inversion Principle
