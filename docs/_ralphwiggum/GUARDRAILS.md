# Ralph Wiggum Guardrails (Persistent Notes)

This document is a **living record** of guardrails, failure patterns, and “gotchas” observed while running long autonomous loops in this repo.

**Goal:** prevent repeated mistakes across sessions by making lessons durable.

---

## How to Use

- When a failure pattern is observed (reward hacking attempt, repeated CI failure, spec ambiguity), add an entry under **Observed Failure Patterns**.
- When we change the protocol/prompt/quality gates to address a pattern, record it under **Guardrail Changes** with the commit hash.
- Keep entries concrete and actionable (symptom → root cause → mitigation).

---

## Observed Failure Patterns

### FP-001: “Passes locally, fails in CI” drift

- Symptom: developer runs a subset of checks; CI fails on a different gate.
- Common cause: local workflow doesn’t run `make ci` (or pre-commit) before pushing.
- Mitigation: treat `make ci` as the minimum bar before every commit; keep CI and Makefile aligned.

### FP-002: Hung iteration (no progress, no output)

- Symptom: the loop stalls on an iteration (e.g., tool invocation never returns).
- Mitigation: enforce per-iteration timeouts and capture logs under `logs/ralph/` for post-mortem.

---

## Guardrail Changes (Protocol/Prompt/CI)

- 2026-01-19: Added iteration + total runtime timeouts and per-iteration logs (`logs/ralph/`) to the recommended loop commands.
