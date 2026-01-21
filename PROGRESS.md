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

- [x] **DEBT-034**: Hardcoded `MAX_SIZE` constant
  - Deck: `docs/_archive/debt/debt-034-hardcoded-max-size.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

- [x] **DEBT-035**: `type: ignore` in exit paths
  - Deck: `docs/_archive/debt/debt-035-type-ignore-exit-paths.md`
  - Acceptance: Satisfy the deck acceptance criteria; `make ci` green.

---

## Spec Queue (After Debt Complete)

- [x] **SPEC-020**: OpenAlex Integration
  - Spec: `docs/_archive/specs/spec-020-openalex-integration.md`
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-021**: Aristotle Integration
  - Spec: `docs/_archive/specs/spec-021-aristotle-integration.md`
  - Target: v1.2+
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-013**: Logging & Evaluation
  - Spec: `docs/_archive/specs/spec-013-logging-evaluation.md`
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-012**: Loop Command
  - Spec: `docs/_archive/specs/spec-012-loop-command.md`
  - Design: `docs/_archive/specs/spec-012-design.md` (Complete)
  - Target: v1.2
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-016**: Formal Conjectures Integration
  - Spec: `docs/_archive/specs/spec-016-formal-conjectures.md`
  - Target: v1.4
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-014**: Vector Embeddings
  - Spec: `docs/_archive/specs/spec-014-vector-embeddings.md`
  - Target: v1.3
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: Requires `sentence-transformers` optional dep.

- [x] **SPEC-015**: Batch Operations
  - Spec: `docs/_archive/specs/spec-015-batch-operations.md`
  - Target: v1.3
  - Acceptance: All spec acceptance criteria met; `make ci` green.

- [x] **SPEC-017**: MCP Server
  - Spec: `docs/_archive/specs/spec-017-mcp-server.md`
  - Target: v1.4
  - Acceptance: All spec acceptance criteria met; `make ci` green.
  - Note: Requires `mcp[cli]` optional dep.

- [x] **SPEC-019**: PDF Conversion
  - Spec: `docs/_archive/specs/spec-019-pdf-conversion.md`
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

### 2026-01-20: DEBT-034 Hardcoded MAX_SIZE constant removed

**Files modified:**
- `src/erdos/core/arxiv_client.py` - Imported `MAX_TEX_FILE_SIZE` from constants; replaced local `MAX_SIZE` variable with the constant
- `docs/debt/debt-034-hardcoded-max-size.md` - Status updated to Fixed (archived)
- `docs/debt/README.md` - Moved DEBT-034 to Archived

**Note:** Pure DRY refactoring - no behavior change. The constant `MAX_TEX_FILE_SIZE` (2 MiB) was already defined in constants.py but not used in arxiv_client.py.

### 2026-01-21: DEBT-035 type: ignore suppressions removed from exit paths

**Files modified:**
- `src/erdos/commands/app_context.py` - Changed return type from `tuple[AppContext | None, CLIOutput | None]` to `tuple[AppContext, None] | tuple[None, CLIOutput]` to express invariant that exactly one of context/error is non-None
- `src/erdos/commands/show.py` - Refactored guard pattern: separate checks for `app_error is not None` and `app_ctx is None` to enable mypy type narrowing
- `src/erdos/commands/ingest.py` - Same guard pattern refactor
- `src/erdos/commands/ask.py` - Same guard pattern refactor
- `src/erdos/commands/refs.py` - Same guard pattern refactor
- `src/erdos/commands/lean.py` - Same guard pattern refactor
- `src/erdos/commands/list_cmd.py` - Same guard pattern refactor
- `docs/debt/debt-035-type-ignore-exit-paths.md` - Status updated to Fixed
- `docs/debt/README.md` - Moved DEBT-035 to Archived

**Solution:** Changed combined guard `if app_error is not None or app_ctx is None:` to two sequential checks. First check exits on error, second check (unreachable by invariant) allows mypy to narrow `app_ctx` to non-None.

### 2026-01-21: SPEC-020 OpenAlex Integration implemented

**Files created:**
- `src/erdos/core/openalex_client.py` - OpenAlex API client with OpenAlexConfig, OpenAlexClient, and helper functions (reconstruct_abstract, extract_arxiv_id, find_pdf_url, openalex_to_reference, _map_oa_status)
- `tests/unit/test_openalex_client.py` - 36 unit tests covering config, helpers, client methods, and OA status mapping
- `tests/integration/test_openalex_integration.py` - Integration tests for live OpenAlex API (marked requires_network)

**Files modified:**
- `src/erdos/core/models/reference.py` - Added new fields: pdf_url, openalex_id, cited_by_count, concepts (list), oa_status (OpenAccessStatus enum)
- `src/erdos/core/models/__init__.py` - Exported OpenAccessStatus enum
- `src/erdos/core/ingest/fetch.py` - Added MetadataSource enum (OPENALEX, ARXIV, CROSSREF); added _fetch_openalex_by_doi(), _fetch_openalex_by_arxiv(); updated fetch_reference_entry() to accept source parameter (default: OPENALEX)
- `src/erdos/core/ingest/__init__.py` - Re-exported MetadataSource enum
- `src/erdos/core/ingest/service.py` - Added source parameter to ingest_problem_references()
- `src/erdos/commands/ingest.py` - Added --source flag (openalex|arxiv|crossref); updated IngestOptions dataclass
- `tests/unit/test_ingest_service.py` - Updated tests to specify source=MetadataSource.ARXIV or CROSSREF for backward compatibility
- `tests/integration/test_cli_ingest.py` - Added --source crossref to tests using Crossref mocks
- `tests/unit/test_ingest_command_helpers.py` - Added source field to IngestOptions tests and mock assertions

**Features:**
- OpenAlex as primary metadata source (271M+ works)
- Unified API for DOI and arXiv lookups
- Abstract reconstruction from OpenAlex inverted index format
- Open access status mapping (gold, green, bronze, hybrid, closed)
- PDF URL extraction from primary and alternate locations
- Citation count and concept tags from OpenAlex
- Retry logic with exponential backoff for transient failures
- --source flag allows selecting metadata backend (openalex, arxiv, crossref)

### 2026-01-21: SPEC-021 Aristotle Integration implemented

**Files created:**
- `src/erdos/core/aristotle.py` - Aristotle subprocess wrapper with AristotleError, AristotleConfig, AristotleResult, validate_aristotle_config(), build_aristotle_command(), run_aristotle_prove_from_file()
- `tests/unit/test_aristotle.py` - 26 unit tests covering config, validation, command building, execution, and error handling
- `tests/integration/test_cli_lean_prove.py` - 13 integration tests for CLI command validation, config, execution, options, and JSON output

**Files modified:**
- `src/erdos/commands/lean.py` - Added `prove_with_aristotle()` core logic function; added `prove` subcommand with --output, --timeout, --informal, --formal-input-context options; added `_print_human_prove_result()` handler
- `docs/specs/spec-021-aristotle-integration.md` - Status updated to Complete (archived)
- `docs/specs/README.md` - Moved SPEC-021 from Deferred to Archived

**Features:**
- `erdos lean prove` command runs Aristotle theorem prover via subprocess
- Requires ARISTOTLE_API_KEY environment variable (ConfigError if missing)
- Optional ERDOS_ARISTOTLE_COMMAND to specify custom aristotle executable
- Output file required and must differ from input (UsageError protection)
- --timeout for subprocess timeout (default 600s)
- --informal and --formal-input-context flags passed to Aristotle
- JSON output with CLIOutput envelope and aristotle execution details
- Exit codes: SUCCESS, USAGE_ERROR, NOT_FOUND, CONFIG_ERROR, ERROR

### 2026-01-21: SPEC-013 Logging & Evaluation implemented

**Files created:**
- `src/erdos/core/run_logger.py` - Run logging module with RunLogEntry, RunLogger, generate_run_id(), parse_since(), get_run_logger()
- `src/erdos/commands/logs.py` - CLI command for querying/summarizing logs with filters (--problem-id, --command, --since, --status, --limit, --summary)
- `tests/unit/test_run_logger.py` - 31 unit tests for log entry creation, sanitization, querying, filtering, and summaries
- `tests/integration/test_cli_logs.py` - 13 integration tests for logs command and integration with other commands
- `logs/.gitkeep` - Ensure logs directory exists

**Files modified:**
- `src/erdos/commands/presenter.py` - Added run logging in `exit_with_result()` to automatically log all CLI command invocations
- `src/erdos/cli.py` - Registered logs command
- `.gitignore` - Added `logs/*.jsonl` pattern for run logs

**Features:**
- Automatic structured logging for every CLI command invocation
- JSON Lines format (`.jsonl`) for machine parsing
- Each log entry captures: command, args (sanitized), timestamp, duration_ms, success/failure, problem_id, result summary
- Args sanitization redacts keys containing "key", "token", "secret", "password", "credential"
- `erdos logs` command with filters: --problem-id, --command, --since, --status, --limit
- `erdos logs --summary` for aggregated statistics (by command, by problem, metrics)
- Support for relative time (7d, 2h, 30m) and ISO 8601 in --since
- Human-readable table output and JSON output via global --json flag
- Logs command itself excluded from logging to avoid recursion
- Run log stored in `logs/runs.jsonl` (gitignored)

### 2026-01-21: SPEC-012 Loop Command implemented

**Files created:**
- `src/erdos/core/loop_config.py` - LoopConfig frozen dataclass with CLI options (max_iterations, max_patch_lines/bytes, stall_threshold, lean_timeout, etc.)
- `src/erdos/core/patch_validator.py` - SEARCH/REPLACE block parsing, match finding, keyword counting, bracket balance checking, PatchResult/PatchStatus/MatchStatus enums
- `src/erdos/core/loop_verifier.py` - LoopVerification dataclass, LoopExitCondition enum, sorry/admit counting with word boundaries
- `src/erdos/templates/loop_prompt.j2` - Jinja2 template for LLM prompts with file content, errors, problem context, and output format constraints
- `src/erdos/core/loop.py` - Main orchestration: LoopResult/LoopStatus, IterationRecord, LoopLogger (JSONL logging), run_loop() function with safety guardrails
- `src/erdos/commands/loop.py` - CLI command `erdos loop run` with --max-iter, --no-apply, --timeout, --allow-sorry-increase, --max-patch-lines/bytes, --rag-limit, --llm-cmd options
- `tests/unit/test_loop_config.py` - Tests for LoopConfig defaults, custom values, from_cli(), immutability
- `tests/unit/test_patch_validator.py` - Tests for SEARCH/REPLACE parsing, match finding, keyword counting, bracket balance, patch validation
- `tests/unit/test_loop_verifier.py` - Tests for sorry/admit counting, LoopVerification properties, exit conditions
- `tests/unit/test_loop.py` - Tests for budget_context, build_loop_prompt, apply_patch, run_loop with mocked LLM
- `tests/integration/test_cli_loop.py` - Integration tests for CLI help, options, JSON output

**Files modified:**
- `src/erdos/cli.py` - Registered loop command
- `docs/_archive/specs/spec-012-loop-command.md` - Status updated to Complete (archived)
- `docs/_archive/specs/spec-012-design.md` - Status updated to Complete (archived)
- `docs/specs/README.md` - Updated v1.2 to DONE; moved SPEC-012 and 012-DESIGN to Archived

**Features:**
- Iterative "propose → apply → check" cycle for Lean formalization
- SEARCH/REPLACE block parsing with strict validation (exact match only)
- Sorry/admit injection prevention (rejects patches adding placeholders)
- Bracket balance checking for syntax sanity
- File shrinkage detection (rejects >20% file size reduction)
- Stall detection with configurable threshold
- JSONL logging per run with schema versioning
- External LLM execution via ERDOS_LLM_COMMAND or --llm-cmd
- Safety: only modifies files under formal/lean/Erdos/

### 2026-01-21: SPEC-016 Formal Conjectures Integration implemented

**Files created:**
- `src/erdos/core/formal_conjectures.py` - Module for upstream formalization detection, fetching, caching, and provenance tracking
- `tests/unit/test_formal_conjectures.py` - 37 unit tests for metadata parsing, URL building, sorry detection, SHA-256 hashing, provenance, and fetch with cache
- `tests/integration/test_lean_import.py` - 16 integration tests for erdos lean status, erdos lean import, --import-upstream flag, and provenance tracking

**Files modified:**
- `src/erdos/commands/lean.py` - Added `status` and `import` subcommands; added `--import-upstream` and `--no-network` options to `formalize`; added helper functions for status checking, import operations, and human output formatting
- `docs/specs/spec-016-formal-conjectures.md` - Status updated to Complete
- `docs/specs/README.md` - Moved SPEC-016 from Deferred to Archived; updated v1.4 to PARTIAL
- `pyproject.toml` - Added TC003 and PTH109 to test file ignores

**Features:**
- `erdos lean status [PROBLEM_ID]` shows formalization status (upstream metadata + local file)
- `erdos lean import PROBLEM_ID` fetches and imports upstream formalization from google-deepmind/formal-conjectures
- `--no-network` flag uses cached upstream files only (errors if not cached)
- `--dry-run` shows what would be imported without writing
- `--force` overwrites existing local file with different content
- `--skip-lean-validation` skips Lean type checking on imported files
- `erdos lean formalize --import-upstream` imports upstream instead of generating skeleton
- Provenance tracking in `formal/lean/Erdos/.provenance.yaml` (SHA-256, timestamps, source URLs)
- Cache stored in `formal/lean/.upstream_cache/` for offline use
- Sorry/admit detection for local files
- Exit codes: SUCCESS, NOT_FOUND, NETWORK_ERROR, LEAN_ERROR, CONFIG_ERROR

### 2026-01-21: SPEC-014 Vector Embeddings implemented

**Files created:**
- `src/erdos/core/embeddings.py` - Embedding model wrapper with EmbeddingConfig, EmbeddingModel, cosine_similarity(), embedding_to_blob(), embedding_from_blob(), get_embedding_model()
- `tests/unit/test_embeddings.py` - 18 unit tests for EmbeddingConfig, EmbeddingModel mocking, cosine similarity, and blob serialization
- `tests/unit/test_search_index_embeddings.py` - 21 unit tests for embedding schema, build_embeddings, has_embeddings, search_semantic, search_hybrid
- `tests/integration/test_search_semantic.py` - Integration tests for CLI help, mode validation, BM25-only mode, embedding dependency handling, JSON output

**Files modified:**
- `pyproject.toml` - Added `embeddings` optional dependency (sentence-transformers, numpy); added mypy override for sentence_transformers
- `src/erdos/core/search_index.py` - Added EmbeddingModelProtocol, SemanticSearchResult dataclass, chunk_embeddings table, set_embedding_metadata(), get_embedding_metadata(), has_embeddings(), build_embeddings(), search_semantic(), search_hybrid()
- `src/erdos/core/ports.py` - Extended SearchIndexProtocol with embedding methods (has_embeddings, get_embedding_metadata, set_embedding_metadata, build_embeddings, search_semantic, search_hybrid)
- `src/erdos/commands/search.py` - Added SearchMode enum (BM25, SEMANTIC, HYBRID), extended SearchOptions with embedding fields, added CLI flags (--semantic, --hybrid, --bm25-only, --alpha, --build-embeddings, --embedding-model), added helpers for embedding operations and result formatting

**Features:**
- `erdos search --semantic` for pure vector similarity search
- `erdos search --hybrid` for combined BM25 + semantic ranking with --alpha weight
- `erdos search --bm25-only` for explicit BM25-only mode
- `erdos search --build-embeddings` generates embeddings for all indexed chunks
- `erdos search --embedding-model MODEL` selects embedding model (default: all-MiniLM-L6-v2)
- Embeddings stored in SQLite chunk_embeddings table with model/dimension metadata
- Model mismatch detection prevents searching with incompatible embeddings
- Cosine similarity normalized to 0..1 range for score mixing
- Graceful degradation when sentence-transformers not installed (BM25 works without extra deps)

### 2026-01-21: SPEC-015 Batch Operations implemented

**Files created:**
- `src/erdos/core/rate_limiter.py` - Simple rate limiter with configurable delay, sleep_if_needed(), time_until_next_call(), reset()
- `src/erdos/core/batch.py` - Batch operations module with BatchFilters, BatchState, BatchResult, BatchRunner, filter_problems(), generate_batch_id(), state file persistence
- `tests/unit/test_rate_limiter.py` - 14 unit tests for rate limiter initialization, timing, reset behavior
- `tests/unit/test_batch.py` - 45 unit tests for filters, state, result, batch runner with mocked execution
- `tests/integration/test_batch_operations.py` - 16 integration tests for CLI batch ingest and batch formalize

**Files modified:**
- `src/erdos/commands/ingest.py` - Extended IngestOptions with batch fields (all_problems, status, prize_min, prize_max, tags, limit, skip, resume, dry_run, max_concurrent); added batch mode logic with --all, --status, --tag, --dry-run, --resume flags; integrated rate limiter and batch runner
- `src/erdos/commands/lean.py` - Added batch_formalize() function with ThreadPoolExecutor parallel execution; added batch formalize subcommand to CLI
- `tests/unit/test_ingest_command_helpers.py` - Updated tests for new _run_single_ingestion function signature
- `docs/specs/spec-015-batch-operations.md` - Status updated to Complete
- `docs/specs/README.md` - Moved SPEC-015 from Deferred to Archived; marked v1.3 as DONE

**Features:**
- `erdos ingest --all` processes all problems matching filters
- `erdos ingest --status open` filters by problem status
- `erdos ingest --tag NUMBER_THEORY` filters by problem tags
- `erdos ingest --prize-min 100 --prize-max 500` filters by prize range
- `erdos ingest --limit 10 --skip 5` for pagination
- `erdos ingest --dry-run` shows what would be processed without executing
- `erdos ingest --resume` continues from last batch state
- Rate limiting with configurable delay (default 3.0s between problems)
- Batch state persisted to `.erdos/batch/` for resume support
- `erdos lean batch-formalize` processes multiple problems with parallel execution
- `--max-concurrent` controls parallelism (default 4 for formalize)
- Progress callbacks for UI updates during batch operations

### 2026-01-21: SPEC-017 MCP Server implemented

**Files created:**
- `src/erdos/mcp/__init__.py` - MCP package for erdos-banger
- `src/erdos/mcp/server.py` - MCP server with FastMCP tools (get_problem, list_problems, get_references, search_index, lean_check, lean_formalize, ask_question, get_logs)
- `tests/unit/test_mcp_tools.py` - 22 unit tests for MCP tool functions with fixture data
- `tests/integration/test_mcp_server.py` - 10 integration tests for server module and tool return formats

**Files modified:**
- `pyproject.toml` - Added `mcp` optional dependency (`mcp[cli]>=1.25.0,<2`); added `erdos-mcp` entry point; added mypy override for mcp module
- `docs/specs/spec-017-mcp-server.md` - Status updated to Complete
- `docs/specs/README.md` - Moved SPEC-017 from Deferred to Archived; updated v1.4 to DONE

**Features:**
- `erdos-mcp` entry point to start MCP server via stdio transport
- Core tools: get_problem, list_problems, get_references, search_index, lean_check, lean_formalize
- Optional tools: ask_question (RAG with no_llm=True default), get_logs (run log queries)
- All tools return CLIOutput-compatible JSON strings with schema_version
- Path traversal protection in lean_check (rejects `../` patterns)
- Tools reuse existing core logic (no shell subprocess calls)
- Tests guarded with `pytest.importorskip("mcp")` for optional dependency

### 2026-01-21: SPEC-019 PDF Conversion implemented

**Files created:**
- `src/erdos/core/pdf_converter.py` - PDF converter abstraction with PDFConverter enum, LLMService enum, PDFConversionConfig, PDFConversionResult, is_marker_available(), is_pdfplumber_available(), get_available_converters(), select_converter(), convert_with_pdfplumber(), convert_with_marker(), convert_pdf()
- `src/erdos/commands/convert.py` - Standalone `erdos convert` command with --output, --format, --converter, --use-llm, --llm-service, --force-ocr options
- `tests/unit/test_pdf_converter.py` - 21 unit tests for converter detection, enums, config, results, and conversion functions
- `tests/integration/test_pdf_convert.py` - 10 integration tests for CLI command help, validation, output formats, and options
- `tests/integration/test_pdf_ingest.py` - 6 integration tests for ingest command PDF options (--pdf, --no-pdf, --pdf-converter, --use-llm)

**Files modified:**
- `src/erdos/cli.py` - Registered convert command
- `src/erdos/commands/ingest.py` - Added PDF options to IngestOptions dataclass (pdf, pdf_converter, use_llm); added CLI options (--pdf, --no-pdf, --pdf-converter, --use-llm)
- `src/erdos/core/literature_paths.py` - Added get_pdf_cache_path(), get_pdf_extract_path(), sanitize_reference_id() for PDF storage paths
- `pyproject.toml` - Added per-file ignores for TC003 (Path runtime usage); added mypy overrides for marker and pdfplumber optional dependencies
- `docs/specs/spec-019-pdf-conversion.md` - Status updated to Complete
- `docs/specs/README.md` - Moved SPEC-019 from Deferred to Archived; updated v2.0 to DONE

**Features:**
- `erdos convert paper.pdf` for standalone PDF conversion
- Marker (GPL) as primary converter for high-quality math extraction
- pdfplumber (MIT) as fallback for basic text extraction
- LLM-enhanced extraction via --use-llm and --llm-service options
- PDF options on ingest command (--pdf, --no-pdf, --pdf-converter, --use-llm)
- Output formats: markdown (default), text, json
- Automatic converter detection and fallback

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
