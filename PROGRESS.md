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
- [x] [SPEC-035] (4/5) Implement forum proof-link extraction + unit tests (HTML fixtures); write `data/sync_cache/proofs/<id>/links.json`
- [x] [SPEC-035] (5/5) Implement `erdos sync proof <id> --verify` (opt-in) + provenance/log writing + tests (offline fixtures + `requires_network` smoke)

### SPEC-029: Exa Research API Integration

- [x] [SPEC-029] (1/2) Implement `ExaClient` + caching + unit tests (no network; use `responses`)
- [x] [SPEC-029] (2/2) Implement `erdos research exa` command + tests (offline); add `requires_network` smoke test (skipped by default)

### SPEC-030: Semantic Scholar API Integration

- [x] [SPEC-030] (1/2) Implement `SemanticScholarClient` + caching + unit tests (offline)
- [x] [SPEC-030] (2/2) Implement `erdos refs s2 {citations,cited-by,references}` + tests (offline); add `requires_network` smoke test

### SPEC-031: zbMATH Open API Integration

- [x] [SPEC-031] (1/3) Implement `ZbMathClient` + caching + unit tests (offline)
- [x] [SPEC-031] (2/3) Implement `erdos refs zbmath` + tests (offline); add `requires_network` smoke test
- [x] [SPEC-031] (3/3) Add `erdos search --msc` mode + tests (offline)

### SPEC-032: Multi-Model Routing (External Command)

- [x] [SPEC-032] (1/3) Add task→LLM-command router (`src/erdos/core/llm/*`) + unit tests (no CLI wiring)
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
- 2026-01-24: [SPEC-035] (4/5) ✅ Implemented `erdos sync proof <id>` forum extraction. 4 HTML fixtures, 36 unit tests (25 forum.py + 11 proof_cmd.py). Extracts GitHub/GitLab links, author, Lean version hints. Writes links.json to sync cache. CI passes (80.55% coverage). Commit: 26b373a.
- 2026-01-24: [SPEC-035] (5/5) ✅ Implemented `erdos sync proof <id> --verify` with security guardrails. 25 unit tests (proofs.py) + 18 CLI tests (proof_cmd.py) + 6 integration tests. Clones repos to temp dir, runs `lake build` with timeouts, verifies no-sorries, saves provenance + logs. Added DEBT-092 exemption for LOC. CI passes (80.64% coverage). Commit: 6389c20.
- 2026-01-24: [SPEC-029] (1/2) ✅ Implemented `ExaClient` + caching + 30 unit tests. Rate limiting (1 req/sec), retry with backoff, 24h cache TTL, arXiv/DOI extraction. Added DEBT-093 exemption for LOC (+18). CI passes (80.76% coverage). Commit: c27848c.
- 2026-01-24: [SPEC-029] (2/2) ✅ Implemented `erdos research exa search` command. 12 unit tests + 2 requires_network integration tests. Added `--save-leads` for lead creation, `ERDOS_EXA_CACHE_PATH` for test isolation. CI passes (80.77% coverage). Commit: ac82f85.
- 2026-01-24: [SPEC-030] (1/2) ✅ Implemented `SemanticScholarClient` + caching + 30 unit tests. S2Paper/CitationContext/S2Reference models, rate limiting (3s unauth/1s auth), retry with backoff, 7-day cache TTL. Added DEBT-094 exemption for LOC (+184). CI passes (80.88% coverage). Commit: 1afe110.
- 2026-01-24: [SPEC-030] (2/2) ✅ Implemented `erdos refs s2 {citations,cited-by,references}` commands + backward compat. Added RefsGroup(TyperGroup) for `erdos refs <id>` compat. 13 unit tests + 6 integration tests. All acceptance criteria met. CI passes (80.64% coverage). Commit: d0bc1da.
- 2026-01-24: [SPEC-031] (1/3) ✅ Implemented `ZbMathClient` + caching + 36 unit tests. ZbMathEntry/MSCCode models, rate limiting (2s delay), retry with backoff, 30-day cache TTL. DOI/zbl_id/MSC/title search. Added DEBT-095 exemption for LOC (+287). CI passes (80.56% coverage). Commit: 8dd89eb.
- 2026-01-24: [SPEC-031] (2/3) ✅ Implemented `erdos refs zbmath` commands (lookup by DOI/zbl_id/title + MSC search). 14 unit tests + 7 integration tests. Full JSON/human output support. CI passes (80.91% coverage). Commit: 546d15b.
- 2026-01-24: [SPEC-031] (3/3) ✅ Implemented `erdos search --msc` mode for zbMATH MSC code search. Added --year-min/--year-max filters. 13 unit tests + 2 integration tests. Added DEBT-095/096 exemptions. CI passes (81.03% coverage). Commit: 931ec36.
- 2026-01-24: [SPEC-032] (1/3) ✅ Implemented task→LLM-command router (`src/erdos/core/llm/*`). TaskType enum + get_env_var_chain() + resolve_llm_command() with override support. 22 unit tests covering resolution order, empty/missing env vars, override bypass. Added router.py to DEBT-075 env allowlist. CI passes (81.09% coverage). Commit: 150a549.
