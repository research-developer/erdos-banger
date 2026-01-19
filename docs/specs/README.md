# Specifications

Design specifications for the erdos-banger CLI toolkit.

## Version Roadmap

```text
v1.0 (DONE)     Foundation: CLI, data loading, search, Lean integration
v1.1 (PENDING)  Literature: Ingest + RAG Q&A
v1.2 (DEFERRED) Iteration: Loop command + logging
v1.3 (FUTURE)   Enhancement: Vectors + batch ops
v1.4 (FUTURE)   Integration: Formal conjectures + MCP
v2.0 (BLOCKED)  Expansion: PDF conversion
```

## Active Specs

Specs currently in progress or awaiting implementation.

| ID | Title | Status | Target | Description |
|----|-------|--------|--------|-------------|
| 010 | [Ingest Command](spec-010-ingest-command.md) | Pending | v1.1 | Literature ingestion: arXiv cache + Crossref metadata |
| 011 | [Ask Command](spec-011-ask-command.md) | Pending | v1.1 | RAG prompt builder + optional LLM via subprocess |

## Design Documents

Research-backed design decisions for complex specs.

| ID | Title | Status | Prerequisite For |
|----|-------|--------|------------------|
| 012-DESIGN | [Loop Command Design](spec-012-design.md) | Approved | SPEC-012 |

## Deferred Specs

Specs designed for future versions.

| ID | Title | Status | Target | Description |
|----|-------|--------|--------|-------------|
| 012 | [Loop Command](spec-012-loop-command.md) | Deferred (blocked by 012-DESIGN) | v1.2 | Iterative LLM-assisted Lean proof attempts |
| 013 | [Logging & Evaluation](spec-013-logging-evaluation.md) | Deferred | v1.2 | Structured run logs + progress tracking |
| 014 | [Vector Embeddings](spec-014-vector-embeddings.md) | Deferred | v1.3 | Semantic search via embeddings |
| 015 | [Batch Operations](spec-015-batch-operations.md) | Deferred | v1.3 | Batch ingest/formalize with rate limiting |
| 016 | [Formal Conjectures](spec-016-formal-conjectures.md) | Deferred | v1.4 | Import existing formalizations |
| 017 | [MCP Server](spec-017-mcp-server.md) | Deferred | v1.4 | Model Context Protocol for AI integration |
| 019 | [PDF Conversion](spec-019-pdf-conversion.md) | Ready | v2.0 | PDF to text with math preservation (Marker + LLM) |
| 020 | [OpenAlex Integration](spec-020-openalex-integration.md) | Ready | v1.2 | Primary academic metadata source (271M+ works) |

## Archived Specs

Completed specs that are fully implemented.

| ID | Title | Location |
|----|-------|----------|
| 001 | Dev Environment & Tooling | [archive](../_archive/specs/spec-001-dev-environment-tooling.md) |
| 002 | Testing Strategy | [archive](../_archive/specs/spec-002-testing-strategy.md) |
| 003 | Domain Models | [archive](../_archive/specs/spec-003-domain-models.md) |
| 004 | CLI Architecture | [archive](../_archive/specs/spec-004-cli-architecture.md) |
| 005 | Problem Loader | [archive](../_archive/specs/spec-005-problem-loader.md) |
| 006 | Search Index | [archive](../_archive/specs/spec-006-search-index.md) |
| 007 | Lean Integration | [archive](../_archive/specs/spec-007-lean-integration.md) |
| 008 | Test Fixtures | [archive](../_archive/specs/spec-008-test-fixtures.md) |
| 009 | Architecture Cleanup | [archive](../_archive/specs/spec-009-architecture-cleanup.md) |
| 018 | DevX Makefile | [spec](spec-018-devx-makefile.md) (Complete) |

**Next Spec ID:** SPEC-021

## Dependency Graph

```text
v1.0 Foundation (DONE)
├── 001 Dev Environment
├── 002 Testing Strategy
├── 003 Domain Models
├── 004 CLI Architecture
├── 005 Problem Loader
├── 006 Search Index
├── 007 Lean Integration
├── 008 Test Fixtures
└── 009 Architecture Cleanup

v1.1 Literature (PENDING)
├── 010 Ingest Command ────────────┐
└── 011 Ask Command ←──────────────┘ (uses the local search index; ingested extracts become usable once indexed)

v1.2 Iteration & Metadata (DEFERRED)
├── 012-DESIGN Loop Design ←── research (approved SSOT)
├── 012 Loop Command ←── 012-DESIGN + 011 Ask + 007 Lean
├── 013 Logging ←── all commands (tracks progress)
└── 020 OpenAlex Integration ←── augments 010 Ingest

v1.3 Enhancement (FUTURE)
├── 014 Vector Embeddings ←── 006 Search Index
└── 015 Batch Operations ←── 010 Ingest + 007 Lean

v1.4 Integration (FUTURE)
├── 016 Formal Conjectures ←── 007 Lean
└── 017 MCP Server ←── all CLI commands

v2.0 Expansion (READY)
└── 019 PDF Conversion ←── 010 Ingest (Marker + LLM enhancement)
```

## Master Documents

- [Master Vision](./master-vision.md) - Full design & build plan
- [Master Qualifications](./master-qualifications.md) - Project scope & requirements

## Spec Lifecycle

1. **Draft** - Initial design, open for discussion
2. **Pending** - Approved, awaiting implementation
3. **Deferred** - Intentionally postponed to a later version
4. **Active** - Implementation in progress
5. **Complete** - Fully implemented and tested
6. **Archived** - Completed, locked in
7. **Blocked** - Cannot proceed due to external dependency

## Writing a New Spec

Each spec must be:

1. **Self-contained** - Clear scope, explicit dependencies
2. **Vertical slice** - Testable end-to-end
3. **Independently verifiable** - Tests don't require unimplemented specs

Template sections:
- Scope (in/out)
- CLI Interface
- Output Schema (JSON)
- Implementation (modules to create/modify)
- Verification (testable claims)
- References
- Changelog
