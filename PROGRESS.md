# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-24
**Status:** Ready - New spec implementation sprint (v3.2+)
**Branch:** ralph-wiggum-next
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code for behavior changes
3. **No reward hacks**
   - never delete/disable tests to "make CI green"
   - never mock the unit under test (mock boundaries only: network/subprocess/time)
   - never lower quality gates (coverage/lint/mypy)
4. **Checkpoint discipline**
   - commit after each completed task
   - push after each commit (remote is the backup)
5. **Escalate early** (stop and request human review) if:
   - a spec/deck contradicts SSOT / code reality
   - the change exceeds ~500 LOC or >10 files for a single task (split into subtasks)
   - quality gates fail after 3 fix attempts for the same root cause

---

## Active Queue (One Task Per Iteration)

Work strictly top-to-bottom unless blocked by dependencies.

### SPEC-035: Unified Problem Data Sync

- [x] [SPEC-035] (1/5) Define sync cache schemas + pure merge logic for `data/problems_enriched.yaml` (submodule + website) + unit tests (no network)
- [x] [SPEC-035] (2/5) Implement `erdos sync website <id>` using HTML fixtures + unit tests; ensure output stays `ProblemLoader`-compatible
- [x] [SPEC-035] (3/5) Implement `erdos sync submodule` + offline `--check` mode; add `requires_network` test for remote freshness
- [ ] [SPEC-035] (4/5) Implement forum proof-link extraction + unit tests (HTML fixtures); write `data/sync_cache/proofs/<id>/links.json`
- [ ] [SPEC-035] (5/5) Implement `erdos sync proof <id> --verify` (opt-in) + provenance/log writing + tests (offline fixtures + `requires_network` smoke)

### SPEC-029: Exa Research API Integration

- [ ] [SPEC-029] (1/2) Implement `ExaClient` + caching + unit tests (no network; use `responses`)
- [ ] [SPEC-029] (2/2) Implement `erdos research exa` command + tests (offline); add `requires_network` smoke test (skipped by default)

### SPEC-030: Semantic Scholar API Integration

- [ ] [SPEC-030] (1/2) Implement `SemanticScholarClient` + caching + unit tests (offline)
- [ ] [SPEC-030] (2/2) Implement `erdos refs s2 {citations,cited-by,references}` + tests (offline); add `requires_network` smoke test

### SPEC-031: zbMATH Open API Integration

- [ ] [SPEC-031] (1/3) Implement `ZbMathClient` + caching + unit tests (offline)
- [ ] [SPEC-031] (2/3) Implement `erdos refs zbmath` + tests (offline); add `requires_network` smoke test
- [ ] [SPEC-031] (3/3) Add `erdos search --msc` mode + tests (offline)

### SPEC-032: Multi-Model Routing (External Command)

- [ ] [SPEC-032] (1/3) Add task→LLM-command router (`src/erdos/core/llm/*`) + unit tests (no CLI wiring)
- [ ] [SPEC-032] (2/3) Wire router into `erdos ask` default LLM command selection + tests (preserve `--llm-cmd` override)
- [ ] [SPEC-032] (3/3) Wire router into `erdos loop run` default LLM command selection + tests (preserve `--llm-cmd` override)

### SPEC-033: Lean Copilot Integration

- [ ] [SPEC-033] (1/3) Add optional deps for copilot server (FastAPI/uvicorn) per spec + unit test scaffolding
- [ ] [SPEC-033] (2/3) Implement minimal `erdos lean copilot serve` (`/generate`) using SPEC-032 routing + unit tests (offline)
- [ ] [SPEC-033] (3/3) Implement `/encode` (embeddings) with a clear degraded mode + unit tests

### SPEC-034: Progress Dashboard

- [ ] [SPEC-034] (1/2) Implement dashboard aggregation (`src/erdos/core/dashboard/data.py`) + unit tests (JSON snapshot contract)
- [ ] [SPEC-034] (2/2) Implement `erdos dashboard` UI (Rich) + tests; ensure `erdos --json dashboard` is non-interactive

---

## Work Log

- 2026-01-24: [SPEC-035] (1/5) ✅ Verified sync cache schemas + merge logic already implemented in `src/erdos/core/sync/{models,merge}.py` with 57 unit tests passing. CI passes (81.55% coverage).
- 2026-01-24: [SPEC-035] (2/5) ✅ Implemented `erdos sync website <id>` with HTML fixtures (4 files), 37 unit tests (94 total sync tests). JSON output contract validated. ProblemLoader-compatible. CI passes (80.77% coverage). Commit: 0216497.
- 2026-01-24: [SPEC-035] (3/5) ✅ Implemented `erdos sync submodule` + `--check` mode. 31 unit tests + 4 integration tests (requires_network). Fixed DEBT-075 violation (added ERDOS_SUBMODULE_PATH to AppConfig). CI passes (80.55% coverage). Commit: 3d5df70.
