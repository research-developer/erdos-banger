# Spec 027: Loop → Research Integration

> Writes a structured attempt record after `erdos loop` runs and injects `SYNTHESIS.md` into the loop prompt context.

**Status:** Archived
**Target:** v3.0
**Prerequisites (SSOT):**
- Loop command: `docs/_archive/specs/spec-012-loop-command.md`
- Research workspace: `docs/_archive/specs/spec-023-research-workspace.md`
- Research records: `docs/_archive/specs/spec-024-research-records.md`
- Index research artifacts: `docs/_archive/specs/spec-025-index-research-artifacts.md`

---

## 0) Scope (v3.0)

### In scope

1) After `erdos loop run PROBLEM_ID` returns a `LoopResult` (success or failure):
   - Write a new attempt record file under `research/problems/{id:04d}/attempts/att_*.yaml`.
   - The record must include pointers to:
     - Lean file path
     - loop run log path (`logs/loop/*.jsonl`)
2) Always include `SYNTHESIS.md` content in the loop prompt context when present.

### Out of scope

- Any long-running campaign orchestration (Temporal/LangGraph, etc.)
- Indexing scratchpad into loop context (explicitly excluded for v3)

---

## 1) Attempt Record Mapping (authoritative)

### Record kind

`kind: lean_loop`

### Result mapping

Map loop status to attempt result:

- `success` → `success`
- everything else → `failed`

### Summary mapping (deterministic)

`summary` must include:
- loop status
- iterations completed
- sorry/admit counts before/after for the final applied patch (if available)

The goal is to make the attempt record navigable without opening raw logs.

---

## 2) Implementation (modules / wiring)

### Loop prompt context

- `src/erdos/core/loop/runner.py` (or `execute_proof_loop` service)
  - Load `SYNTHESIS.md` (if present) and pass it as a RAG/context chunk into prompt construction.

### Attempt record write

- Add a small integration layer under `src/erdos/core/research/loop_integration.py`:
  - `write_attempt_from_loop_result(problem_id, loop_result, repo_root) -> Path`

This must:
- create the research workspace if missing (call SPEC-023 init logic)
- write a new attempt record (SPEC-024 schema)

---

## 3) Verification (TDD; testable claims)

### Unit tests

1) Given a synthetic `LoopResult` object, `write_attempt_from_loop_result` writes a valid attempt YAML matching schema.
2) Prompt injection:
   - Given a synthesis string and a minimal Lean file, `build_loop_prompt` output includes the synthesis content.

### Integration tests

1) `erdos loop` creates an attempt record:
   - Create a workspace for problem 6.
   - Create a minimal Lean file with `sorry` so the loop exits early with `LLM_REQUIRED` (no `lake` needed).
   - Run `erdos --json loop run 6 --no-apply --path <tmp/lean>`.
   - Assert a new file exists in `research/problems/0006/attempts/` and references the loop log path.

All integration tests must set:
- `ERDOS_DATA_PATH`
- `ERDOS_REPO_ROOT`

---

## 4) Changelog

- v1 (Complete): Loop writes attempt record + includes synthesis in prompt context.
