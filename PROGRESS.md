# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-19
**Status:** Active (Technical Debt Sprint)
**Branch:** ralph-wiggum-debt
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

### Technical Debt Sprint (Recommended Order)

Per `docs/debt/README.md`, these are the active debt items ordered by recommended resolution:

- [x] **DEBT-020**: Magic Numbers and Naming - Define constants, use ExitCode enum
  - Spec: `docs/debt/debt-020-magic-numbers-and-naming.md`
  - Acceptance: `constants.py` created, all `[:200]` → `PREVIEW_LENGTH`, all `code=3` → `ExitCode.NOT_FOUND`, all `code=2` → `ExitCode.USAGE_ERROR`

- [x] **DEBT-018-A**: DRY - Extract arXiv download helper (CRITICAL)
  - Spec: `docs/debt/debt-018-dry-violations.md` (Section 4)
  - Acceptance: arXiv download logic exists in exactly ONE place, both call sites use it

- [ ] **DEBT-018-B**: DRY - Extract stable key function
  - Spec: `docs/debt/debt-018-dry-violations.md` (Section 5)
  - Acceptance: Stable key function exists in ONE place, handles both ReferenceEntry and ReferenceRecord

- [ ] **DEBT-018-C**: DRY - Extract time measurement helper
  - Spec: `docs/debt/debt-018-dry-violations.md` (Section 2)
  - Acceptance: Time measurement helper/context manager, used in all 9 command locations

- [ ] **DEBT-017**: Function Length Violations - Extract helper functions
  - Spec: `docs/debt/debt-017-function-length-violations.md`
  - Acceptance: Remove `# noqa: PLR0911,PLR0912,PLR0915` suppressions, no function >50 lines

- [ ] **DEBT-016**: SRP Violation in models.py - Split into focused modules
  - Spec: `docs/debt/debt-016-srp-models-violation.md`
  - Acceptance: `models/` package with focused modules, backward-compatible imports, each module <150 lines

- [ ] **DEBT-019**: Dependency Inversion Violations - Add protocols and context
  - Spec: `docs/debt/debt-019-dependency-inversion-violations.md`
  - Acceptance: `ProblemRepository` protocol, `AppContext` container, no `from_default()` in business logic

- [ ] **DEBT-021**: Missing Abstractions - Add Repository/Service patterns
  - Spec: `docs/debt/debt-021-missing-abstractions.md`
  - Acceptance: Service layer exists, Repository pattern implemented

---

## Guidelines

- **DEBT-* tasks follow TDD** - write tests for new behavior BEFORE refactoring
- **Pure refactors** should not change behavior - existing tests must pass
- **One task per iteration** - do not batch tasks
- **Quality gates must pass** before marking complete
- **Atomic commits** with proper format: `[DEBT-XXX] Type: description`

---

## Work Log

- 2026-01-19: Created ralph-wiggum-debt branch for technical debt sprint
- 2026-01-19: Set up PROGRESS.md with 6 active debt items from docs/debt/README.md
- 2026-01-19: [DEBT-020] Fixed magic numbers and naming - Created constants.py, replaced all [:200] with PREVIEW_LENGTH, replaced code=3 with ExitCode.NOT_FOUND, replaced code=2 with ExitCode.USAGE_ERROR, refactored internal boolean variables to use positive names (no_llm→enable_llm, no_download→allow_download, no_network→allow_network). Files: src/erdos/core/constants.py (new), tests/unit/test_constants.py (new), src/erdos/core/models.py, src/erdos/core/search_index.py, src/erdos/core/ask.py, src/erdos/commands/search.py, src/erdos/commands/show.py, src/erdos/commands/refs.py, src/erdos/commands/lean.py, src/erdos/commands/list_cmd.py, src/erdos/core/ingest.py
- 2026-01-19: [DEBT-018-A] Fixed arXiv download duplication - Extracted _download_and_extract_arxiv helper function with ArxivDownloadResult dataclass, replaced both duplication sites (DOI+arXiv and arXiv-only cases). Files: src/erdos/core/ingest.py, tests/unit/test_ingest_service.py

---

## Completion Criteria

The queue is complete when:
1. All `[ ]` items in Active Queue are `[x]`
2. `make ci` passes
3. `make smoke` passes
4. All debt documents updated with "Fixed" status and commit hashes

The loop operator verifies completion via this file's state (no unchecked items), not by parsing model output.

---

## Rollback / Recovery (If Something Goes Sideways)

- Abort the loop: stop the process / kill the tmux session.
- Inspect current state: `git status`, `git log -10 --oneline`.
- To undo the last commit (keep working tree changes): `git reset --soft HEAD~1`
- To undo the last commit (discard working tree changes): `git reset --hard HEAD~1`
- To revert a commit on a shared branch: `git revert <sha>`
