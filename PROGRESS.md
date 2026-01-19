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

- [ ] **SPEC-010**: Ingest Command → `docs/specs/spec-010-ingest-command.md`
- [ ] **SPEC-011**: Ask Command → `docs/specs/spec-011-ask-command.md`

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

- [ ] **FINAL-GATES**: All quality gates pass (`make ci`)
- [ ] **FINAL-SMOKE**: Smoke test passes (`make smoke`)

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
├── SPEC-010 Ingest Command
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
