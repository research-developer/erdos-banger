# erdos-banger - Ralph Wiggum Progress Tracker

**Last Updated:** 2026-01-18
**Status:** Active (Ready to Start)
**Branch:** ralph-wiggum-v1.1
**Purpose:** State file for Ralph Wiggum loop (see `docs/_ralphwiggum/protocol.md`)

---

## Active Queue

### Phase 1: v1.1 Literature (Critical Path)

- [ ] **SPEC-010**: Ingest Command → `docs/specs/spec-010-ingest-command.md`
- [ ] **SPEC-011**: Ask Command → `docs/specs/spec-011-ask-command.md`

### Phase 2: v1.2 Iteration (Deferred but Ready)

- [ ] **SPEC-012-DESIGN**: Loop Command Design Decisions → `docs/specs/spec-012-design.md` *(senior review required)*
- [ ] **SPEC-012**: Loop Command → `docs/specs/spec-012-loop-command.md` *(blocked by SPEC-012-DESIGN)*
- [ ] **SPEC-013**: Logging & Evaluation → `docs/specs/spec-013-logging-evaluation.md`

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
└── SPEC-011 Ask Command ← uses 010 for ingested content (optional)

v1.2 Iteration
├── SPEC-012-DESIGN Loop Design Decisions ← research-backed, needs senior review
├── SPEC-012 Loop Command ← blocked by SPEC-012-DESIGN + needs 011 Ask + 007 Lean
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
