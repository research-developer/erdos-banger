# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-24
**Status:** Ready - Debt paydown sprint
**Branch:** ralph-wiggum-debt-100-101
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

### DEBT-100: Integration Tests Load `.env` When Present

- [x] [DEBT-100] Load `.env` (if present) for local network tests; document approach; preserve CI determinism

### DEBT-101: Lean/Mathlib Version Upgrade

- [x] [DEBT-101] (1/3) Confirm target Lean/Mathlib versions and update debt doc (no code changes)
- [x] [DEBT-101] (2/3) Upgrade `formal/lean` toolchain + Mathlib pin; make `lake build` pass locally
- [x] [DEBT-101] (3/3) Update fixtures/docs and ensure `test-with-lean` CI job passes

---

## Work Log

- 2026-01-24: Reset sprint queue for DEBT-100/101 (branch: `ralph-wiggum-debt-100-101`). Previous sprint merged to `main`/`dev` via PR #26 (merge commit ea426d8).
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
- 2026-01-24: [SPEC-032] (2/3) ✅ Wired LLM router into `erdos ask` with TaskType.ask_question. Uses ERDOS_LLM_COMMAND_MATH -> ERDOS_LLM_COMMAND chain. Preserves --llm-cmd override and --no-llm behavior. 6 integration tests for router wiring. CI passes (81.09% coverage). Commit: ba3777a.
- 2026-01-24: [SPEC-032] (3/3) ✅ Wired LLM router into `erdos loop run` with TaskType.loop_patch. Uses ERDOS_LLM_COMMAND_CODE -> ERDOS_LLM_COMMAND chain. Preserves --llm-cmd override. 6 integration tests in test_cli_loop_router.py. Updated existing loop tests to provide ERDOS_LLM_COMMAND. CI passes (80.97% coverage). Commit: 83465f3.
- 2026-01-24: [SPEC-033] (1/3) ✅ Added `copilot` optional extra (fastapi>=0.115.0, uvicorn>=0.32.0). Created src/erdos/lean_copilot package with is_copilot_available() and CopilotNotAvailableError. Added mypy overrides for FastAPI. 6 unit tests. CI passes (80.98% coverage). Commit: ab08be3.
- 2026-01-24: [SPEC-033] (2/3) ✅ Implemented `erdos lean copilot serve` with `/generate` endpoint. FastAPI server with tactic suggestions via SPEC-032 router. Tactic parsing (bullets, comments, punctuation cleanup). 44 unit tests (server.py + copilot_cmd.py). CI passes (80.62% coverage). Commit: 718b292.
- 2026-01-24: [SPEC-033] (3/3) ✅ Implemented `/encode` endpoint with embeddings (SPEC-014) + degraded mode (HTTP 503). Added embeddings.py wrapper with is_embeddings_available(), EmbeddingsNotAvailableError, encode_texts(), model caching. 23 unit tests (test_embeddings.py + test_server.py). CI passes (80.61% coverage). Commit: 2d4f974.
- 2026-01-24: [SPEC-034] (1/2) ✅ Implemented dashboard aggregation (`src/erdos/core/dashboard/data.py`). DashboardData + ProblemStats dataclasses, aggregate_dashboard_data() with filtering, problem status (new/active/stale), attempt timeline, to_dict() JSON snapshot. 20 unit tests. CI passes (80.82% coverage). Commit: 3a81101.
- 2026-01-24: [SPEC-034] (2/2) ✅ Implemented `erdos dashboard` CLI UI (Rich). Problem overview table, attempt timeline heatmap, aggregate stats panel. State machine (state.py) for keyboard navigation (q/r/p/a/b). --problem detail view, --recent time filter, --refresh auto-refresh. Non-interactive JSON mode (erdos --json dashboard). 45 unit tests (state.py + render.py + CLI). Refactored dashboard() to pass LOC audit. CI passes (80.69% coverage). Commit: 38c826c.
- 2026-01-24: [DEBT-100] ✅ Added pytest-dotenv for `.env` loading in local tests. Fixed tests expecting unset vars. Documented in AGENTS.md. CI passes (80.23% coverage). Commit: 8410c4f.
- 2026-01-24: [DEBT-101] (1/3) ✅ Confirmed target versions: Lean 4.27.0 + Mathlib 4.27.0 (Jan 23-24, 2026). Documented 4 stable Mathlib imports. Decision: keep test fixtures at current versions. CI passes (80.27% coverage). Commit: 8ca56bb.
- 2026-01-24: [DEBT-101] (2/3) ✅ Upgraded toolchain to Lean v4.27.0 + Mathlib v4.27.0. Fixed import path (`Mathlib.Algebra.BigOperators.Group.Finset` → `Mathlib.Algebra.BigOperators.Group.Finset.Basic`). `lake build` passes (773 jobs). CI passes (80.27% coverage). Commit: 986035f.
- 2026-01-24: [DEBT-101] (3/3) ✅ Verified `make ci` passes. Fixed missing skip logic in `test_cli_loop_router.py` and `test_loop_research_integration.py`. CLI commands (`erdos lean check/formalize`) work correctly. Archived DEBT-100 and DEBT-101. Commit: 2ebb005.
