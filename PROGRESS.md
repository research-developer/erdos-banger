# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-20
**Status:** Ready - Debt Sprint (DEBT-026, 027, 028)
**Branch:** ralph-wiggum
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code
3. **No reward hacks**:
   - never delete/disable tests to "make CI green"
   - never mock the unit under test (mock only boundaries: network/subprocess/time)
   - never lower quality gates (coverage, lint, mypy)
4. **Checkpoint discipline**:
   - commit after each completed task
   - push after each commit (remote is the backup)
5. **Escalate early** (stop and request human review) if:
   - a spec is ambiguous or contradicts SSOT
   - required deps are missing / incompatible
   - quality gates fail after 3 fix attempts
   - the change would exceed ~500 LoC or touch >10 files for a single task

## Active Queue

- [x] **DEBT-026**: Long functions remain (≥ 80 LOC)
  - Deck: `docs/debt/debt-026-long-functions-remain.md`
  - Acceptance: Each core function ≥80 LOC is reduced below 80 LOC, or explicitly justified with an inline "linear parsing" rationale; new helpers are pure where possible with unit tests; `make ci` green.

- [ ] **DEBT-027**: Broad `except Exception` catches (masking risk)
  - Deck: `docs/debt/debt-027-broad-exception-catches.md`
  - Acceptance: Core service layers no longer use `except Exception` except where re-raising after cleanup; CLI boundary code returns friendly errors but retains debug signal; `make ci` green.

- [ ] **DEBT-028**: Ingest manifest churn (non-idempotent writes)
  - Deck: `docs/debt/debt-028-ingest-manifest-churn.md`
  - Acceptance: Running `erdos ingest <id>` twice with `--no-network --no-download` produces no file diffs when no content changes; clear policy on whether `literature/manifests/` is tracked or local-only; `make ci` green.

---

## Guidelines

- **DEBT-* tasks follow TDD** - write tests for new behavior BEFORE refactoring
- **Pure refactors** should not change behavior - existing tests must pass
- **One task per iteration** - do not batch tasks
- **Quality gates must pass** before marking complete
- **Atomic commits** with proper format: `[DEBT-XXX] Type: description`

---

## Work Log

### 2026-01-20: DEBT-026 Long functions refactored

**Files modified:**
- `src/erdos/core/lean_runner.py` - Extracted `_resolve_lean_path`, `_build_check_result`, `_timeout_result` from `check()` (98→30 LOC)
- `src/erdos/core/ingest/fetch.py` - Extracted `_build_manifest_entry_with_arxiv`, `_fetch_doi_with_arxiv`, `_fetch_doi_only`, `_fetch_arxiv_only` from `fetch_reference_entry()` (96→29 LOC); extracted `_error_result`, `_success_result` from `process_single_reference()` (88→33 LOC)
- `src/erdos/core/problem_loader.py` - Extracted `_validate_list_field`, `_parse_references`, `_validate_required_fields` from `_parse_problem()` (83→28 LOC)
- `docs/debt/debt-026-long-functions-remain.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-026 to Archived

**Note:** `list_`, `search` CLI commands already well-factored (LOC includes Typer option declarations). `ingest_problem_references` already has helpers; actual logic is 64 LOC.

(entries added by Ralph loop as tasks complete)

---

## Completion Criteria

The queue is complete when:
1. All `[ ]` items in Active Queue are `[x]`
2. `make ci` passes
3. `make smoke` passes
4. All debt documents updated with "Fixed" status and commit hashes

The loop operator verifies completion via this file's state (no unchecked items), not by parsing model output.

---

## Rollback / Recovery

- Abort the loop: stop the process / kill the tmux session.
- Inspect current state: `git status`, `git log -10 --oneline`.
- To undo the last commit (keep working tree changes): `git reset --soft HEAD~1`
- To undo the last commit (discard working tree changes): `git reset --hard HEAD~1`
- To revert a commit on a shared branch: `git revert <sha>`
