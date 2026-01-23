# Spec 026: Deterministic Research Synthesis

> Adds `erdos research synthesize` that deterministically generates/updates `SYNTHESIS.md` from scratchpad + structured records (no LLM).

**Status:** Archived
**Target:** v3.0
**Prerequisites (SSOT):**
- Research workspace: `docs/_archive/specs/spec-023-research-workspace.md`
- Research records: `docs/_archive/specs/spec-024-research-records.md`

---

## 0) Scope (v3.0)

### In scope

1) Implement `erdos research synthesize PROBLEM_ID`:
   - Reads:
     - `SCRATCHPAD.md`
     - records in `leads/`, `attempts/`, `hypotheses/`, `tasks/`
   - Writes:
     - `SYNTHESIS.md` deterministically (no LLM)
2) Synthesis output must be stable for identical inputs (byte-for-byte).

### Out of scope

- LLM-assisted synthesis (explicitly forbidden for v3 canonical synthesis)
- Indexing (handled in SPEC-025)

---

## 1) CLI Interface

```text
erdos research synthesize PROBLEM_ID
```

Behavior:
- Must not require network.
- Must not call any LLM.
- If files are missing, treat them as empty (workspace must still synthesize).

---

## 2) Synthesis Template (authoritative)

`SYNTHESIS.md` must follow this structure:

```md
# Synthesis: Problem 0006
_Last updated: 2026-01-23_

## Summary
- (one sentence placeholder if empty)

## Top tasks (by priority)
- ...

## Active hypotheses
- ...

## Key leads (by priority)
- ...

## Recent attempts (most recent first)
- ...

## Notes (recent scratchpad excerpts)
- ...
```

Rules:
- Dates are derived from current UTC time at synthesis execution.
- Lists are sorted deterministically:
  - tasks: `priority desc`, then `created_at asc`
  - active hypotheses: `created_at asc`
  - leads: `priority desc`, then `updated_at desc`
  - attempts: `created_at desc`
- Limit list sizes to keep synthesis short:
  - tasks: top 10
  - hypotheses: all `active` (max 10)
  - leads: top 10
  - attempts: last 5

---

## 3) Output Schema (JSON)

`erdos research synthesize` `data` must include:

```json
{
  "problem_id": 6,
  "synthesis_path": "…/research/problems/0006/SYNTHESIS.md",
  "written_bytes": 1234,
  "counts": {
    "tasks": 3,
    "hypotheses": 1,
    "leads": 2,
    "attempts": 5
  }
}
```

---

## 4) Implementation (modules / wiring)

- `src/erdos/core/research/synthesis.py`
  - Read inputs, compute deterministic view model, render markdown.
- Extend `src/erdos/commands/research.py`
  - Add `synthesize` subcommand.

---

## 5) Verification (TDD; testable claims)

### Unit tests

1) Deterministic render:
   - Given fixed inputs and a frozen “now”, output markdown matches a golden string.
2) Sorting rules:
   - Ensure ordering matches spec.

### Integration tests

1) End-to-end synthesis:
   - Create workspace + add one of each record type + write scratchpad.
   - Run `erdos --json research synthesize 6`.
   - Assert `SYNTHESIS.md` exists and contains expected sections.

Note: If time-freezing dependency is not available, tests should validate structure and ordering rather than exact timestamp string.

---

## 6) Changelog

- v1 (Complete): Deterministic synthesis generator.
