# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-22
**Status:** Ready - Debt First (Search/Loop Cleanups)
**Branch:** ralph-wiggum-consolidated
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
   - a debt doc contradicts SSOT / code reality
   - the change exceeds ~500 LOC or >10 files for a single task (split into subtasks)
   - quality gates fail after 3 fix attempts for the same root cause

---

## Active Queue (Debt Before Specs)

Work strictly top-to-bottom unless blocked by dependencies.

- [x] **DEBT-061**: Remove core backward-compatibility shims
  Deck: `docs/_archive/debt/debt-061-remove-core-compatibility-shims.md`
- [x] **DEBT-060**: Formalize command long Typer callback
  Deck: `docs/_archive/debt/debt-060-formalize-cmd-long-callback.md`
- [x] **DEBT-062**: (Closed) Search service “god module” claim invalid
  Deck: `docs/_archive/debt/debt-062-search-service-god-module.md`
- [x] **DEBT-064**: Inject LLM executor into loop runner (DIP)
  Deck: `docs/_archive/debt/debt-064-loop-runner-dip.md`
- [ ] **DEBT-063**: Split `MetadataProvider` protocol (ISP)
  Deck: `docs/debt/debt-063-metadata-provider-isp.md`
- [ ] **DEBT-065**: Move loop orchestration out of command layer (SRP)
  Deck: `docs/debt/debt-065-thick-cli-callbacks.md`
- [ ] **DEBT-066**: Test directory structure should mirror src/ bounded contexts (CCP)
  Deck: `docs/debt/debt-066-test-structure-mirrors-src.md`

---

## Work Log

- **2026-01-22 (DEBT-060)**: Refactored `formalize_cmd.py` to reduce function LOC. Extracted `_FormalizeArgs` dataclass, `_validate_args()` and `_execute_formalize()` helpers. `register()` now 80 LOC (from 194), `formalize()` now 76 LOC (from 190). Removed DEBT-060 exemptions from audit script. `make ci` passes.
- **2026-01-22 (DEBT-061)**: Removed 10 backward-compatibility shim files from `src/erdos/core/` and updated all imports to use bounded-context modules directly. Added regression guard tests in `test_dependencies.py`. `make ci` passes.
- **2026-01-22 (DEBT-062)**: Closed as invalid after re-auditing SSOT: `core/search/service.py` is 140 LOC and already decomposed; no exemption exists. Archived deck to prevent wasted iterations.
- **2026-01-22 (DEBT-064)**: Injected LLM executor into loop runner (DIP compliance). Added `LLMExecute` protocol to `ports.py`, updated `run_loop()` and `_run_single_iteration()` to accept injected `llm_execute` dependency with default. Refactored 3 tests to pass `llm_execute=fake_llm` instead of patching module globals. `make ci` passes.
