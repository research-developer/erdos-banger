# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-21
**Status:** Ready - Debt Sprint + Spec Implementation
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

- [x] **DEBT-029**: Logging coverage gaps
  - Deck: `docs/debt/debt-029-no-logging-usage.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-030**: Redundant dual `--json` flag
  - Deck: `docs/_archive/debt/debt-030-redundant-json-flag.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-031**: API rate limiting missing / constant unused
  - Deck: `docs/_archive/debt/debt-031-no-api-rate-limiting.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-032**: HTTP responses not closed properly
  - Deck: `docs/_archive/debt/debt-032-http-response-not-closed.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-033**: No retry logic for network failures
  - Deck: `docs/_archive/debt/debt-033-no-retry-logic.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-034**: Hardcoded `MAX_SIZE` constant
  - Deck: `docs/debt/debt-034-hardcoded-max-size.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [ ] **DEBT-035**: `type: ignore` in exit paths
  - Deck: `docs/debt/debt-035-type-ignore-exit-paths.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

---

## Spec Queue (After Debt Complete)

- [ ] **SPEC-020**: OpenAlex Integration
  - Spec: `docs/specs/spec-020-openalex-integration.md`
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-021**: Aristotle Integration
  - Spec: `docs/specs/spec-021-aristotle-integration.md`
  - Target: v1.2+
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-013**: Logging & Evaluation
  - Spec: `docs/specs/spec-013-logging-evaluation.md`
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-012**: Loop Command
  - Spec: `docs/specs/spec-012-loop-command.md`
  - Design: `docs/specs/spec-012-design.md` (Approved)
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-016**: Formal Conjectures Integration
  - Spec: `docs/specs/spec-016-formal-conjectures.md`
  - Target: v1.4
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-014**: Vector Embeddings
  - Spec: `docs/specs/spec-014-vector-embeddings.md`
  - Target: v1.3
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: Requires `sentence-transformers` optional dep.

- [ ] **SPEC-015**: Batch Operations
  - Spec: `docs/specs/spec-015-batch-operations.md`
  - Target: v1.3
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [ ] **SPEC-017**: MCP Server
  - Spec: `docs/specs/spec-017-mcp-server.md`
  - Target: v1.4
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: Requires `mcp[cli]` optional dep.

- [ ] **SPEC-019**: PDF Conversion
  - Spec: `docs/specs/spec-019-pdf-conversion.md`
  - Target: v2.0
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: Requires `marker` external dep; most complex spec.

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

### 2026-01-20: DEBT-029 Logging coverage gaps fixed

**Files modified:**
- `src/erdos/core/crossref_client.py` - Added logger, DEBUG logs for request timing/response size
- `src/erdos/core/arxiv_client.py` - Added DEBUG logs for request timing/response size
- `src/erdos/core/index_builder.py` - Added logger, INFO logs for build start/finish, DEBUG progress
- `src/erdos/core/search_index.py` - Added logger, DEBUG for init, INFO for clear operations
- `src/erdos/core/ingest/fetch.py` - Enhanced DEBUG logs for arXiv downloads/extracts, WARNING on failures
- `src/erdos/core/ask/llm.py` - Added DEBUG logs for LLM execution timing and response size
- `docs/debt/debt-029-no-logging-usage.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-029 to Archived

**Verified:** `--log-level DEBUG` now produces useful timing/progress output for API calls and batch operations.

### 2026-01-20: DEBT-030 Redundant --json flag removed

**Files modified:**
- `src/erdos/commands/list_cmd.py` - Removed `json_output` parameter and `set_json_mode()` call
- `src/erdos/commands/show.py` - Removed `json_output` parameter and `set_json_mode()` call
- `src/erdos/commands/refs.py` - Removed `json_output` parameter and `set_json_mode()` call
- `src/erdos/commands/search.py` - Removed `json_output` parameter and `set_json_mode()` call
- `src/erdos/commands/ask.py` - Removed `json_output` parameter and `set_json_mode()` call; updated `_show_progress_message` call
- `src/erdos/commands/ingest.py` - Removed `json_output` parameter and `set_json_mode()` call; removed `json_output` from `IngestOptions` dataclass
- `src/erdos/commands/lean.py` - Removed `json_output` parameter from init/check/formalize; removed `set_json_mode()` calls
- `src/erdos/commands/presenter.py` - Removed `set_json_mode()` function
- `tests/e2e/test_cli_show.py` - Updated tests to use global `--json` flag
- `tests/integration/test_cli_commands.py` - Updated tests to use global `--json` flag
- `tests/integration/test_cli_ingest.py` - Updated tests to use global `--json` flag
- `tests/integration/test_cli_ask.py` - Updated tests to use global `--json` flag
- `tests/unit/test_ingest_command_helpers.py` - Removed `json_output` from test cases
- `docs/_archive/debt/debt-030-redundant-json-flag.md` - Status updated to Fixed (archived)
- `docs/debt/README.md` - Moved DEBT-030 to Archived

**Breaking change:** The `--json` flag must now be placed before the command (e.g., `erdos --json show 6` instead of `erdos show 6 --json`).

### 2026-01-20: DEBT-031 Rate limiting centralized

**Files modified:**
- `src/erdos/commands/ingest.py` - Import `API_RATE_LIMIT_DELAY`; use as default for `--delay` option and `IngestOptions.delay`
- `src/erdos/core/ingest/service.py` - Import `API_RATE_LIMIT_DELAY`; use as default for `delay` parameter
- `src/erdos/core/constants.py` - Enhanced docstring documenting per-reference throttling strategy
- `docs/debt/debt-031-no-api-rate-limiting.md` - Status updated to Fixed (archived)
- `docs/debt/README.md` - Moved DEBT-031 to Archived

**Decision:** Per-reference throttling (not per-request). Each reference makes at most 1-3 API requests, so a 3-second delay between references satisfies typical API rate limits.

### 2026-01-20: DEBT-032 HTTP responses use context managers

**Files modified:**
- `src/erdos/core/crossref_client.py` - Wrap `requests.get()` in `with` statement for proper connection cleanup
- `src/erdos/core/arxiv_client.py` - Wrap `requests.get()` in `with` statement for proper connection cleanup
- `src/erdos/core/ingest/fetch.py` - Wrap `requests.get()` in `with` statement for proper connection cleanup
- `docs/_archive/debt/debt-032-http-response-not-closed.md` - Status updated to Fixed (archived)
- `docs/debt/README.md` - Moved DEBT-032 to Archived

**Note:** Pure refactoring - no behavior change. Context managers ensure HTTP connections are released promptly, avoiding potential resource leaks in high-volume scenarios.

### 2026-01-20: DEBT-033 Retry logic for transient network failures

**Files modified:**
- `src/erdos/core/constants.py` - Added retry constants: `RETRY_MAX_ATTEMPTS`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`, `RETRYABLE_STATUS_CODES`
- `src/erdos/core/retry.py` - New module with `fetch_with_retry()`, `is_retryable_error()`, `is_retryable_status_code()` functions
- `src/erdos/core/crossref_client.py` - Updated `fetch_crossref_work()` to use `fetch_with_retry()`
- `src/erdos/core/arxiv_client.py` - Updated `fetch_arxiv_atom()` to use `fetch_with_retry()`
- `src/erdos/core/ingest/fetch.py` - Updated `download_and_extract_arxiv()` to use `fetch_with_retry()`
- `tests/unit/test_retry.py` - Added 28 new tests for retry logic
- `docs/_archive/debt/debt-033-no-retry-logic.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-033 to Archived

**Implementation:**
- Exponential backoff with base delay of 2s, max delay of 30s
- Retries on: Timeout, ConnectionError, HTTP 429/500/502/503/504
- No retry on: HTTP 4xx (except 429)
- Respects Retry-After header on 429 responses
- DEBUG logging for retry attempts

(entries added by Ralph loop as tasks complete)

---

## Completion Criteria

The queue is complete when:
1. All `[ ]` items in Active Queue AND Spec Queue are `[x]`
2. `make ci` passes
3. `make smoke` passes
4. All debt documents updated with "Fixed" status and commit hashes
5. All spec documents updated with "Complete" status and commit hashes

The loop operator verifies completion via this file's state (no unchecked items), not by parsing model output.

---

## Rollback / Recovery

- Abort the loop: stop the process / kill the tmux session.
- Inspect current state: `git status`, `git log -10 --oneline`.
- To undo the last commit (keep working tree changes): `git reset --soft HEAD~1`
- To undo the last commit (discard working tree changes): `git reset --hard HEAD~1`
- To revert a commit on a shared branch: `git revert <sha>`
