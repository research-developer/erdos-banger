# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-19
**Status:** Active (Ready to Start)
**Branch:** ralph-wiggum-v1.1
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Operating Rules (SSOT)

1. **One task per iteration** (never batch)
2. **TDD required**: add a failing test before production code
3. **No reward hacks**:
   - never delete/disable tests to “make CI green”
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

### Phase 1: v1.1 Literature (Critical Path)

**Note:** SPEC-010 has been broken down into atomic subtasks per debt-001-spec-010-scope.md

- [x] **SPEC-010-A** [REVIEWED]: Literature path conventions → `literature_paths.py` + tests
- [x] **SPEC-010-B** [REVIEWED]: arXiv client → `arxiv_client.py` + unit tests + fixtures
- [x] **SPEC-010-C** [REVIEWED]: Crossref client → `crossref_client.py` + unit tests + fixtures
- [x] **SPEC-010-D** [REVIEWED]: Ingest core logic → `ingest.py` + unit tests
- [x] **SPEC-010-E** [REVIEWED]: Ingest command → `commands/ingest.py` + integration tests
- [x] **SPEC-011** [REVIEWED]: Ask Command → `docs/specs/spec-011-ask-command.md`

### Phase 2: v1.2 Iteration (Deferred but Ready)

- [x] **SPEC-012-DESIGN**: Loop Command Design Decisions → `docs/specs/spec-012-design.md` *(Approved SSOT)*
- [ ] **SPEC-012**: Loop Command → `docs/specs/spec-012-loop-command.md` *(deferred to v1.2+)*
- [ ] **SPEC-013**: Logging & Evaluation → `docs/specs/spec-013-logging-evaluation.md` *(deferred to v1.2+)*

### Phase 3: v1.3 Enhancement

- [ ] **SPEC-014**: Vector Embeddings → `docs/specs/spec-014-vector-embeddings.md`
- [ ] **SPEC-015**: Batch Operations → `docs/specs/spec-015-batch-operations.md`

### Phase 4: v1.4 Integration

- [ ] **SPEC-016**: Formal Conjectures → `docs/specs/spec-016-formal-conjectures.md`
- [ ] **SPEC-017**: MCP Server → `docs/specs/spec-017-mcp-server.md`

### Phase 5: Final Verification

- [x] **FINAL-GATES**: All quality gates pass (`make ci`)
- [x] **FINAL-SMOKE**: Smoke test passes (`make smoke`)

---

## Blocked/Skipped

| Spec | Status | Reason |
|------|--------|--------|
| SPEC-018 | Complete | DevX Makefile already implemented |
| SPEC-019 | Blocked | Docling typer conflict (v2.0+) |

---

## Guidelines

- **SPEC-* tasks require a follow-up review iteration** with `[REVIEWED]` marker
- **TDD is mandatory** - write failing tests BEFORE implementation
- **One task per iteration** - do not batch tasks
- **Quality gates must pass** before marking complete
- **Atomic commits** with proper format

---

## Dependency Graph

```
v1.1 Literature (START HERE)
├── SPEC-010-A Literature paths
├── SPEC-010-B arXiv client
├── SPEC-010-C Crossref client
├── SPEC-010-D Ingest core logic
├── SPEC-010-E Ingest command
└── SPEC-011 Ask Command ← uses the local search index (ingested extracts become usable once indexed)

v1.2 Iteration
├── SPEC-012-DESIGN Loop Design Decisions ← approved SSOT
├── SPEC-012 Loop Command ← 012-DESIGN + 011 Ask + 007 Lean
└── SPEC-013 Logging ← all commands (tracks progress)

v1.3 Enhancement
├── SPEC-014 Vector Embeddings ← extends 006 Search Index
└── SPEC-015 Batch Operations ← needs 010 Ingest + 007 Lean

v1.4 Integration
├── SPEC-016 Formal Conjectures ← needs 007 Lean
└── SPEC-017 MCP Server ← exposes all CLI commands
```

---

## Work Log

- 2026-01-18: Initial setup - created PROGRESS.md, PROMPT.md, protocol.md
- 2026-01-18: Created SPEC-012-DESIGN with D1-D8 design decisions (vaporware → concrete)
- 2026-01-19: SPEC-010 attempted but exceeds single-iteration scope (>10 files, ~800-1000 LoC)
- 2026-01-19: Created debt-001-spec-010-scope.md documenting scope issue and recommending task breakdown
- 2026-01-19: Updated PROGRESS.md to replace SPEC-010 with atomic subtasks (SPEC-010-A through SPEC-010-E)
- 2026-01-19: SPEC-010-A completed - created `src/erdos/core/literature_paths.py` with path conventions + `tests/unit/test_literature_paths.py` (10 tests, 100% coverage)
- 2026-01-19: SPEC-010-A reviewed and verified - all acceptance criteria met, 100% test coverage, all quality gates pass
- 2026-01-19: SPEC-010-B completed - created `src/erdos/core/arxiv_client.py` with `parse_arxiv_atom()`, `fetch_arxiv_atom()`, `extract_arxiv_text()` + `tests/unit/test_arxiv_client.py` (10 tests) + `tests/unit/test_arxiv_extract.py` (6 tests), added types-requests to dev dependencies, all quality gates pass
- 2026-01-19: SPEC-010-B reviewed and verified - all acceptance criteria met, 89% coverage for arxiv_client.py, all quality gates pass, no TODO/half-measures
- 2026-01-19: SPEC-010-C completed - created `src/erdos/core/crossref_client.py` with `parse_crossref_work()`, `fetch_crossref_work()` + `tests/unit/test_crossref_client.py` (9 tests), 88% coverage for crossref_client.py, all quality gates pass
- 2026-01-19: SPEC-010-C reviewed and verified - all acceptance criteria met, two-layer API (fetch+parse) for network-free testing, proper Crossref polite pool compliance, 88% coverage, all quality gates pass
- 2026-01-19: SPEC-010-D completed - created `src/erdos/core/ingest.py` with `ingest_problem_references()` orchestrating problem loading, metadata fetching (arXiv/Crossref), manifest creation/updates + `tests/unit/test_ingest_service.py` (5 comprehensive tests covering DOI-only, arXiv-only, merged DOI+arXiv, idempotence, flags), 71% coverage for ingest.py, 84% overall, all quality gates pass
- 2026-01-19: SPEC-010-D reviewed and verified - all acceptance criteria met, core orchestration logic complete with proper reference merging/deduplication/idempotence, atomic manifest writes, 84% overall coverage (exceeds 80% requirement), all quality gates pass, no TODO/half-measures
- 2026-01-19: SPEC-010-E completed - created `src/erdos/commands/ingest.py` with full CLI integration (arguments, options, --json support, human output), registered in `src/erdos/cli.py`, added `tests/integration/test_cli_ingest.py` (5 tests), fixed manifest deserialization bug (TypeAdapter with strict=False for enum/datetime conversion), all quality gates pass, 84% overall coverage
- 2026-01-19: SPEC-010-E reviewed and verified - all acceptance criteria met, CLI properly handles all options (--force, --no-download, --no-network, --timeout, --delay, --mailto), --json flag correctly routes output, integration tests cover all key scenarios (JSON output, --no-download, idempotence, NOT_FOUND error, human output), 84% overall coverage, all quality gates pass, no TODO/half-measures
- 2026-01-19: SPEC-011 completed - created `src/erdos/core/ask.py` with `build_prompt()`, `perform_retrieval()`, `execute_llm()`, `ask_question()` + `src/erdos/commands/ask.py` CLI integration + registered in `src/erdos/cli.py`, added `tests/unit/test_ask_prompt.py` (9 tests), `tests/unit/test_ask_retrieval.py` (5 tests), `tests/unit/test_ask_llm.py` (7 tests), `tests/integration/test_cli_ask.py` (8 tests), fixed FTS5 query syntax for special characters, 83% overall coverage, all quality gates pass
- 2026-01-19: SPEC-011 reviewed and verified - all acceptance criteria met, deterministic prompt builder matches spec SSOT template, retrieval uses SearchIndex.search() with problem_id filter, LLM execution with shell=False security, proper exit codes (NOT_FOUND/ERROR/CONFIG_ERROR/USAGE_ERROR), FTS5 query escaping implemented, comprehensive test coverage (21 unit + 8 integration tests), 83% overall coverage, all quality gates pass, no TODO/half-measures
- 2026-01-19: v1.1 Literature phase complete - all Phase 1 specs (SPEC-010-A through SPEC-011) implemented and reviewed, FINAL-GATES and FINAL-SMOKE verified passing, 83% overall coverage, ready for v1.2 planning

---

## Completion Criteria

The queue is complete when:
1. All `[ ]` items in Active Queue are `[x]`
2. All SPEC-* items have `[REVIEWED]` markers
3. `make ci` passes
4. `make smoke` passes

The loop operator verifies completion via this file's state (no unchecked items), not by parsing model output.

---

## Rollback / Recovery (If Something Goes Sideways)

- Abort the loop: stop the process / kill the tmux session.
- Inspect current state: `git status`, `git log -10 --oneline`.
- To undo the last commit (keep working tree changes): `git reset --soft HEAD~1`
- To undo the last commit (discard working tree changes): `git reset --hard HEAD~1`
- To revert a commit on a shared branch: `git revert <sha>`
