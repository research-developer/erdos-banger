# DEBT-076: Group Lean Modules into `core/lean/` Subpackage

**Priority:** P3 (Minor; clean up when touching nearby code)

**Status:** Open

## Problem

Three Lean-related modules in `src/erdos/core/` root form a cohesive domain but are not grouped into a subpackage, violating the documented architectural rule:

> "If a domain grows to 3+ related modules, extract into a subpackage."
> — CLAUDE.md

### Affected Files

| Module | LOC | Responsibility |
|--------|-----|----------------|
| `core/lean_runner.py` | 429 | Lean 4 compilation, error parsing, environment checks |
| `core/formalizer.py` | 87 | Lean skeleton generation from Jinja2 templates |
| `core/aristotle.py` | 301 | Aristotle prover CLI wrapper |

**Total:** 817 LOC across 3 tightly related modules.

## Evidence

### 1. Cohesion Analysis

All three modules share:
- **Domain:** Lean 4 formalization and proof verification
- **Dependencies:** subprocess, pathlib (external tool invocation)
- **Consumers:** `commands/lean/*.py` commands

### 2. Import Graph

```
commands/lean/check_cmd.py   → lean_runner.py
commands/lean/init_cmd.py    → lean_runner.py
commands/lean/import_cmd.py  → lean_runner.py
commands/lean/formalize_cmd.py → formalizer.py
commands/lean/batch_formalize.py → formalizer.py
commands/lean/prove_cmd.py   → aristotle.py
core/loop/service.py         → formalizer.py, lean_runner.py
core/loop/runner.py          → lean_runner.py (type-checking import)
mcp/server.py                → formalizer.py, lean_runner.py
```

All imports come from the same consumer domain (`commands/lean/` and `core/loop/`).

### 3. SOLID Concerns

- **SRP Pressure:** `lean_runner.py` (429 LOC) mixes project initialization, environment detection, error parsing, and compilation execution.
- **No Abstraction:** Commands directly import concrete classes; no protocol abstraction for testing or swapping implementations.

## Proposed Fix

Create `core/lean/` subpackage:

```
core/lean/
├── __init__.py
├── runner.py            # lean_runner.py moved
├── formalizer.py        # formalizer.py moved
├── aristotle.py         # aristotle.py moved
└── types.py             # (Optional) Extract ResolvedLeanPath, LeanEnvironment
```

### Migration Steps

1. Create `core/lean/` directory with `__init__.py`
2. Move the three modules into the subpackage
3. Update all imports in `src/erdos/` + `tests/` to use the new canonical paths.
4. Delete the old `core/*.py` modules (no compatibility shims; this repo is greenfield and already removed other shims in DEBT-061).
5. Update CLAUDE.md to document `core/lean/` as a bounded context.
6. Run `make ci` to verify.

## Acceptance Criteria

- [ ] `core/lean/` directory created with modules moved
- [ ] All imports in `commands/lean/` updated to canonical paths
- [ ] `core/loop/service.py` and `core/loop/runner.py` updated
- [ ] No remaining imports of `erdos.core.(lean_runner|formalizer|aristotle)`
- [ ] CLAUDE.md updated to list `core/lean/` as bounded context
- [ ] `make ci` passes

## Impact

- **Risk:** Low (import updates only, no logic changes)
- **Effort:** ~100-150 lines of import refactoring across ~10 files
- **Benefit:** Clearer domain boundaries, easier navigation, foundation for future protocol abstractions

## References

- CLAUDE.md rule: "If a domain grows to 3+ related modules, extract into a subpackage"
- `commands/lean/` (consumers)
- `core/loop/verifier.py` (consumer)
