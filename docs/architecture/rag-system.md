# RAG System Architecture

This document describes the Retrieval-Augmented Generation (RAG) pipeline used by `erdos ask` (and related retrieval used by `erdos loop`).

This is intentionally a **“how it works today”** doc. Wherever possible, it points at the source-of-truth (SSOT) implementation rather than duplicating large code blocks that can drift.

## SSOT Pointers

- Ask pipeline: `src/erdos/core/ask/`
- Search index (BM25/semantic/hybrid): `src/erdos/core/search/`
- Search schema: `src/erdos/core/search/db.py` (`SCHEMA_SQL`)
- Research workspace paths: `src/erdos/core/research/paths.py`
- Configuration surface: `docs/developer/configuration.md`

## High-Level Flow (`erdos ask`)

```text
question
  |
  v
retrieve_sources (BM25/FTS5, with fallback sources)
  |
  v
build_prompt (deterministic, citation-grounded)
  |
  v
execute_llm_if_enabled (external subprocess; optional)
  |
  v
answer (+ sources, retrieval metadata)
```

`erdos ask` currently uses **BM25/FTS5 retrieval**. Semantic/hybrid search are available via `erdos search --semantic/--hybrid`, but are not wired into `erdos ask` today.

## Retrieval Layer

### BM25 / FTS5 (Always Available)

- Implementation: `src/erdos/core/search/bm25.py` (`BM25Search`)
- Backing store: SQLite index (default: `index/erdos.sqlite`)
- FTS tokenizer: `porter unicode61` (see `src/erdos/core/search/db.py`)
- Ranking: SQLite `bm25(chunks_fts)` (SQLite returns negative scores; code flips to positive)

**Safety**: user-entered queries are normalized via:

- `safe_fts5_query(query, allow_advanced_syntax=True)`

This prevents FTS5 parse failures like `sum-free sets` → `OperationalError: no such column: free` while still supporting phrase/prefix queries (see integration tests in `tests/integration/test_search_index.py`).

### Semantic Search (Optional)

- Implementation: `src/erdos/core/search/embeddings.py` (`EmbeddingModel`)
- Storage: `chunk_embeddings` table (BLOBs) + `schema_meta` (model/dimension metadata)
- Similarity: cosine similarity over stored embeddings (brute-force scan; O(n) per query)
- Requires optional deps: `uv sync --extra embeddings`

### Hybrid Search (Optional)

- Implementation: `src/erdos/core/search/hybrid.py`
- Candidate generation: BM25 top `2 * limit`
- Re-ranking: cosine similarity over those candidates
- Score:

```text
hybrid_score = (1 - alpha) * bm25_normalized + alpha * semantic_score
semantic_score = (cosine_similarity + 1) / 2
```

## Ask Command Orchestration

### Entry Points

- CLI adapter: `src/erdos/commands/ask.py`
- Core service: `src/erdos/core/ask/service.py` (`ask_question`)

### Source Retrieval (`retrieve_sources`)

Implementation: `src/erdos/core/ask/retrieval.py`

Behavior:

1. If the search index has **no chunks**, return fallback sources only.
2. Otherwise:
   - Build a baseline list of fallback sources (statement/notes/synthesis).
   - Run BM25 retrieval scoped to `problem_id`.
   - Combine + de-duplicate by `chunk_id`, preserving baseline-first order.

#### FTS Query Construction

Implementation: `src/erdos/core/ask/retrieval.py` (`perform_retrieval`)

- A “haystack” string is built from `problem.title` + the user question.
- It is converted into a safe FTS query via:
  - `safe_fts5_query(haystack, allow_advanced_syntax=False)`

We explicitly disable advanced syntax here because the query is programmatically constructed from free text; the user may include stray quotes/operators that should not be treated as FTS5 syntax.

#### Fallback Sources

Fallback sources come from:

- Research synthesis (if present): `research/problems/{problem_id:04d}/SYNTHESIS.md`
- Problem statement
- Problem notes (if present)

Paths are derived via `src/erdos/core/research/paths.py` (do not hardcode).

### Prompt Construction (`build_prompt`)

Implementation: `src/erdos/core/ask/prompt.py`

The prompt is deterministic and includes:

- Problem metadata (id/title)
- Full statement
- Notes (or `(none)`)
- Full retrieved sources, numbered for citation (`[1]`, `[2]`, …)
- The user question
- Explicit instructions to cite sources

### LLM Execution

Implementation: `src/erdos/core/ask/llm.py`

- LLM is an external subprocess (shell-free execution via `shlex.split`).
- Prompt is passed via stdin; answer is read from stdout.
- Default timeout: `LLM_COMMAND_TIMEOUT = 300` seconds (`src/erdos/core/constants.py`).

Routing:

- CLI layer resolves the command via SPEC-032 routing (`src/erdos/core/llm/`).
- Users can override with `--llm-cmd` or disable with `--no-llm`.

## Loop RAG (`erdos loop`)

`erdos loop` also supports lightweight RAG context:

- Implementation: `src/erdos/core/loop/service.py` (`_build_rag_chunks`)
- Source: per-problem synthesis at `research/problems/{problem_id:04d}/SYNTHESIS.md`
- The synthesis is split into multiple chunks (best-effort) and passed into the loop prompt.

## Storage (Search Index Schema)

The schema SSOT is `src/erdos/core/search/db.py` (`SCHEMA_SQL`).

Key tables (high level):

- `problems`: problem metadata for indexing
- `chunks`: the canonical text chunks (statement/notes/references/research records)
- `chunks_fts`: FTS5 virtual table over `chunks.text` (external content via `_rowid`)
- `chunk_embeddings`: optional embeddings keyed by `chunk_id`
- `schema_meta`: simple key/value metadata (e.g., embedding model + dimension)

## Configuration

RAG behavior is mostly configuration-free, but these knobs matter:

- `ERDOS_DATA_PATH`: dataset path resolution
- `ERDOS_INDEX_PATH`: search index location
- `ERDOS_LLM_COMMAND*`: task routing for LLM execution
- `ERDOS_LOAD_DOTENV`: `.env` auto-loading toggle (CLI ergonomics)

See `docs/developer/configuration.md` for the full, authoritative list.

## Tests

- Ask retrieval: `tests/unit/ask/test_retrieval.py`
- Search index integration (FTS5 syntax, including hyphen safety): `tests/integration/test_search_index.py`
- Semantic/hybrid search: `tests/integration/test_search_semantic.py`
- Embedding model + serialization: `tests/unit/search/test_embeddings.py`
