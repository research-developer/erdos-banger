# DEBT-092: Proof Verification Module LOC Violations

**Priority:** P4 (Enhancement)
**Status:** Exempted
**Found:** 2026-01-24
**Exempted:** 2026-01-24

## Description

The proof verification implementation (SPEC-035/5) exceeds LOC thresholds:

| Module | LOC | Threshold | Delta |
|--------|-----|-----------|-------|
| `src/erdos/core/sync/proofs.py` | 599 | 500 | +99 |
| `src/erdos/commands/sync/proof_cmd.py` | 441 | 400 | +41 |

## Justification for Exemption

### proofs.py (596 LOC)

This module contains a complete security-focused verification pipeline with 6 bounded contexts:

1. **Environment sanitization** — Strips API keys before subprocess execution
2. **Git clone** — Shallow clone with security guardrails (no hooks, no submodules)
3. **Lake build** — Runs `lake build` with timeouts and log capture
4. **No-sorries check** — Verifies Lean files have no `sorry` statements
5. **Provenance management** — Records verification metadata
6. **Log handling** — Truncates logs to prevent overflow

The module is cohesive: all functions support a single capability (proof verification).
Splitting would require extracting helpers that have no independent use case.

### proof_cmd.py (429 LOC)

This CLI module includes:
- Typer command with options/docstrings (~50 LOC boilerplate)
- Security warning panel (Rich output)
- Human-readable output formatting
- Verification orchestration logic

The marginal violation (+29 LOC) doesn't justify splitting.

## Resolution

Exempted via inline markers near the top of each file:
- `src/erdos/core/sync/proofs.py`: `# exempt: DEBT-092`
- `src/erdos/commands/sync/proof_cmd.py`: `# exempt: DEBT-092`

## Future Refactoring Opportunities

If the module grows further:
1. Extract provenance functions to `sync/provenance.py`
2. Extract log handling to `sync/log_capture.py`
3. Use Typer subapp pattern for verification commands

Currently, the cohesion benefit outweighs the LOC cost.
