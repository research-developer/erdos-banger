# ADR-003: SQLite FTS5 as the Baseline Search Index

**Status:** Accepted
**Date:** 2026-01-25
**Related:** `docs/_archive/specs/spec-006-search-index.md`, `src/erdos/core/search/`

## Context

`erdos-banger` needs fast, local search across:

- problem statements and notes
- ingested literature extracts and metadata
- (v3+) research workspace artifacts

The project goals are:

- **local-first** execution (no required external services)
- **deterministic** behavior (search index can be rebuilt from SSOT files)
- **low operational overhead** for contributors (no extra daemons)

## Decision

Use an on-disk **SQLite FTS5** index as the default, baseline search system.

- Persisted DB path defaults to `index/erdos.sqlite` (gitignored).
- `erdos search --build-index` builds/rebuilds the index deterministically from
  available SSOT artifacts.
- Optional embedding-based search can be layered on (via the embeddings extra),
  but should not be required for core functionality.

## Options Considered

### Option A (Chosen): SQLite FTS5

**Pros**
- Zero external services; works everywhere SQLite works
- Good enough relevance for technical text (BM25)
- Deterministic rebuilds from local artifacts
- Easy test setup (temporary SQLite file or in-memory DB)

**Cons**
- Not a distributed search system
- Relevance and ranking are less configurable than dedicated engines

### Option B: Elasticsearch / OpenSearch

**Pros**
- Powerful ranking and scaling capabilities

**Cons**
- Operationally heavy for a CLI-first repo
- Harder contributor onboarding and testing

### Option C: Postgres + pgvector

**Pros**
- Strong relational + vector querying in one system

**Cons**
- Requires a running DB service; breaks local-first/no-daemon goal

### Option D: Dedicated Vector DB (Qdrant, Pinecone, etc.)

**Pros**
- Great vector similarity performance and tooling

**Cons**
- Adds infrastructure and vendor dependencies
- Not necessary at current scale; reduces determinism

## Consequences

- Search remains fast and usable without any ML dependencies.
- Embeddings remain an **optional enhancement** and should degrade gracefully.
- The canonical sources remain filesystem artifacts; the index is always a
  derived store that can be regenerated.
