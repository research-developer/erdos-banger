# Specifications

Design specifications for the erdos-banger CLI toolkit.

## Version Roadmap

```text
v1.0 (DONE)     Foundation: CLI, data loading, search, Lean integration
v1.1 (DONE)     Literature: Ingest + RAG Q&A
v1.2 (DONE)     Iteration: Loop + logging + OpenAlex metadata
v1.3 (DONE)     Enhancement: Vectors + batch ops
v1.4 (DONE)     Integration: Formal conjectures + MCP
v2.0 (DONE)     Expansion: PDF conversion (Marker + LLM)
v2.1 (DONE)     Architecture: MetadataProvider abstraction
v3.0 (DONE)     Research: Workspace + campaign memory
v3.1 (DONE)     Verification: v3 integration tests
v3.2 (DONE)     Data sync + Research APIs: Unified sync + Exa integration
v3.3 (DONE)     Research APIs: Semantic Scholar integration
v3.4 (DONE)     Research APIs: zbMATH integration
v3.5 (DONE)     Architecture: Multi-model routing
v4.0 (DONE)     Lean: Lean Copilot integration
v4.1 (DONE)     UX: Progress dashboard
```

## Active Specs

No active specs — all current specs have been completed and archived.

## Design Documents

Research-backed design decisions for complex specs.

| ID | Title | Status | Prerequisite For |
|----|-------|--------|------------------|
| RSM-001 | [v3 Research State](../future/research-state-management-v3.md) | Implemented | SPEC-023 → SPEC-027 |

## Deferred Specs

Specs designed for future versions.

| ID | Title | Status | Target | Description |
|----|-------|--------|--------|-------------|
| (none) | | | | |

## Archived Specs

Completed specs that are fully implemented.

| ID | Title | Location |
|----|-------|----------|
| 001 | Dev Environment & Tooling | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-001-dev-environment-tooling.md) |
| 002 | Testing Strategy | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-002-testing-strategy.md) |
| 003 | Domain Models | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-003-domain-models.md) |
| 004 | CLI Architecture | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-004-cli-architecture.md) |
| 005 | Problem Loader | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-005-problem-loader.md) |
| 006 | Search Index | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-006-search-index.md) |
| 007 | Lean Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-007-lean-integration.md) |
| 008 | Test Fixtures | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-008-test-fixtures.md) |
| 009 | Architecture Cleanup | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-009-architecture-cleanup.md) |
| 010 | Ingest Command | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-010-ingest-command.md) |
| 011 | Ask Command | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-011-ask-command.md) |
| 018 | DevX Makefile | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-018-devx-makefile.md) |
| 013 | Logging & Evaluation | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-013-logging-evaluation.md) |
| 020 | OpenAlex Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-020-openalex-integration.md) |
| 021 | Aristotle Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-021-aristotle-integration.md) |
| 012 | Loop Command | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-012-loop-command.md) |
| 012-DESIGN | Loop Command Design | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-012-design.md) |
| 016 | Formal Conjectures | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-016-formal-conjectures.md) |
| 014 | Vector Embeddings | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-014-vector-embeddings.md) |
| 015 | Batch Operations | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-015-batch-operations.md) |
| 017 | MCP Server | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-017-mcp-server.md) |
| 019 | PDF Conversion | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-019-pdf-conversion.md) |
| 022 | MetadataProvider Orchestration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-022-metadata-provider-orchestration.md) |
| 023 | Research Workspace (Filesystem SSOT) | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-023-research-workspace.md) |
| 024 | Research Records (Leads/Attempts/Hypotheses/Tasks) | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-024-research-records.md) |
| 025 | Index Research Artifacts into Search DB | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-025-index-research-artifacts.md) |
| 026 | Deterministic Research Synthesis | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-026-deterministic-research-synthesis.md) |
| 027 | Loop → Research Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-027-loop-research-integration.md) |
| 028 | v3 Integration Verification | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-028-v3-integration-verification.md) |
| 029 | Exa Research Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-029-exa-research-integration.md) |
| 030 | Semantic Scholar Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-030-semantic-scholar-integration.md) |
| 031 | zbMATH Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-031-zbmath-integration.md) |
| 032 | Multi-Model Routing | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-032-multi-model-routing.md) |
| 033 | Lean Copilot Integration | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-033-lean-copilot-integration.md) |
| 034 | Progress Dashboard | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-034-progress-dashboard.md) |
| 035 | Unified Problem Data Sync | [archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/blob/main/docs/_archive/specs/spec-035-unified-problem-data-sync.md) |

**Next Spec ID:** SPEC-036

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

v1.1 Literature (DONE)
├── 010 Ingest Command ────────────┐
└── 011 Ask Command ←──────────────┘ (uses the local search index; ingested extracts become usable once indexed)

v1.2 Iteration & Metadata (DONE)
├── 012-DESIGN Loop Design ←── research (approved SSOT)
├── 012 Loop Command ←── 012-DESIGN + 011 Ask + 007 Lean
├── 013 Logging ←── all commands (tracks progress)
└── 020 OpenAlex Integration ←── augments 010 Ingest

v1.2+ Optional Proving Backend (DONE)
└── 021 Aristotle Integration ←── 007 Lean

v1.3 Enhancement (DONE)
├── 014 Vector Embeddings ←── 006 Search Index (DONE)
└── 015 Batch Operations ←── 010 Ingest + 007 Lean (DONE)

v1.4 Integration (DONE)
├── 016 Formal Conjectures ←── 007 Lean (DONE)
└── 017 MCP Server ←── all CLI commands (DONE)

v2.0 Expansion (DONE)
└── 019 PDF Conversion ←── 010 Ingest (Marker + LLM enhancement)

v2.1 Architecture (DONE)
└── 022 MetadataProvider Orchestration ←── Resolves DEBT-038, enables pluggable sources

v3.0 Research (DONE)
├── 023 Research Workspace ←── Filesystem SSOT for campaign memory
├── 024 Research Records ←── Leads/Attempts/Hypotheses/Tasks CRUD
├── 025 Index Research Artifacts ←── RAG integration
├── 026 Deterministic Synthesis ←── SYNTHESIS.md rendering
└── 027 Loop → Research ←── Attempt records from loop

v3.1 Verification (DONE)
└── 028 v3 Integration Verification ←── Horizontal + vertical tests

v3.2 Data Sync + Research APIs (DONE)
├── 035 Unified Problem Data Sync ←── 028 (verified v3 foundation)
└── 029 Exa Research Integration ←── Agentic literature synthesis

v3.3 Citation Context (DONE)
└── 030 Semantic Scholar Integration ←── Citation context

v3.4 Math Metadata (DONE)
└── 031 zbMATH Integration ←── Math-specific metadata

v3.5 Architecture (DONE)
└── 032 Multi-Model Routing ←── Task-level LLM routing (external commands)

v4.0 Lean Enhancement (DONE)
└── 033 Lean Copilot Integration ←── 032 (needs model routing)

v4.1 UX (DONE)
└── 034 Progress Dashboard ←── 028 (verified v3 foundation)
```

## Master Documents

- [Master Vision](./master-vision.md) - Full design & build plan
- [Master Qualifications](./master-qualifications.md) - Project scope & requirements

## Spec Lifecycle

1. **Draft** - Initial design, open for discussion
2. **Pending** - Approved, awaiting implementation
3. **Ready** - Fully specified and implementable, scheduled for a later version
4. **Deferred** - Intentionally postponed (may require more design work)
5. **Active** - Implementation in progress
6. **Complete** - Fully implemented and tested
7. **Archived** - Completed, locked in
8. **Blocked** - Cannot proceed due to external dependency

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
