# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-21
**Status:** Ready - Debt Sprint (DEBT-029..DEBT-035)
**Branch:** ralph-wiggum-v1.2
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

- [ ] **DEBT-029**: Logging coverage gaps
  - Deck: `docs/debt/debt-029-no-logging-usage.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-030**: Redundant dual `--json` flag
  - Deck: `docs/debt/debt-030-redundant-json-flag.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-031**: API rate limiting missing / constant unused
  - Deck: `docs/debt/debt-031-no-api-rate-limiting.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-032**: HTTP responses not closed properly
  - Deck: `docs/debt/debt-032-http-response-not-closed.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-033**: No retry logic for network failures
  - Deck: `docs/debt/debt-033-no-retry-logic.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-034**: Hardcoded `MAX_SIZE` constant
  - Deck: `docs/debt/debt-034-hardcoded-max-size.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-035**: `type: ignore` in exit paths
  - Deck: `docs/debt/debt-035-type-ignore-exit-paths.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

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

### 2026-01-20: DEBT-027 Broad exception catches refactored

**Files modified:**
- `src/erdos/core/ingest/service.py` - Changed `except Exception` to `except ProblemLoaderError` in `_load_problem()`
- `src/erdos/core/ask/service.py` - Changed `except Exception` to specific `SearchIndexError | ProblemLoaderError` catches
- `src/erdos/core/ask/llm.py` - Replaced generic exception with `ValueError` handler for shlex errors
- `src/erdos/core/ingest/fetch.py` - Added `logger.exception()` to preserve traceback in last-resort catch
- `src/erdos/commands/list_cmd.py` - Added logging import and `logger.exception()` for debug signal
- `src/erdos/commands/show.py` - Added logging import and `logger.exception()` for debug signal
- `src/erdos/commands/refs.py` - Added logging import and `logger.exception()` for debug signal
- `src/erdos/commands/search.py` - Added logging import and `logger.exception()` for debug signal
- `src/erdos/commands/lean.py` - Added logging import and `logger.exception()` for debug signal
- `tests/unit/test_ask_helpers.py` - Updated tests to use specific exception types
- `docs/debt/debt-027-broad-exception-catches.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-027 to Archived

**Note:** `formalizer.py` already uses proper exception translation pattern (`except Exception as exc: raise FormalizerError(...) from exc`).

### 2026-01-20: DEBT-028 Manifest idempotency implemented

**Files modified:**
- `src/erdos/core/ingest/service.py` - Added `_entries_content_equal()` helper to compare manifest entries excluding operational timestamps; modified `_create_manifest()` to preserve `updated_at` when content unchanged; modified `ingest_problem_references()` to skip writes when content unchanged
- `tests/unit/test_ingest_service.py` - Added 5 new tests: `test_entries_content_equal_same_content`, `test_entries_content_equal_different_content`, `test_entries_content_equal_different_lengths`, `test_ingest_idempotent_no_file_change_on_repeat`, `test_ingest_updates_manifest_when_content_changes`
- `docs/debt/debt-028-ingest-manifest-churn.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-028 to Archived

**Policy decision:** Manifests remain tracked in git (Option B from debt doc). Writes are now idempotent - only update `updated_at` and write file when content actually changes.

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
