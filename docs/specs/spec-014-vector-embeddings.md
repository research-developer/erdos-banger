# Spec 014: Vector Embeddings (Semantic Search)

> Adds semantic search via vector embeddings to complement the existing BM25 index.

**Status:** Pending
**Target:** v1.3
**Prerequisites (SSOT):**
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Domain models: `docs/_archive/specs/spec-003-domain-models.md`
- Presenter utilities (JSON routing): `docs/_archive/specs/spec-009-architecture-cleanup.md`

---

## 0) Scope (v1.3)

### In scope

1. **Embedding generation** for problem statements and ingested content
2. **Vector storage** in SQLite (BLOB columns with numpy serialization)
3. **Semantic search** via cosine similarity
4. **Hybrid ranking** combining BM25 and vector scores
5. **`--semantic` flag** for `erdos search` command

### Out of scope

- External vector databases (Qdrant, Pinecone, pgvector)
- Approximate nearest neighbor (ANN) indexes (FAISS, hnswlib) - deferred until scale requires it
- Fine-tuning embedding models
- GPU acceleration

### Rationale

BM25 is excellent for exact keyword matches but misses semantically related content. For example, searching "prime gaps" won't find content about "consecutive primes" without shared keywords. Vector embeddings capture semantic similarity.

---

## 1) CLI Interface

### 1.1 `erdos search` (Extended)

```text
erdos search QUERY [OPTIONS]
```

**New Options**

- `--semantic, -s`: Use semantic (vector) search instead of BM25
- `--hybrid`: Combine BM25 and semantic scores
- `--bm25-only`: Force BM25-only search (no vectors)
- `--alpha FLOAT`: Hybrid weight (0.0 = BM25 only, 1.0 = semantic only, default: `0.5`)
- `--build-embeddings`: Build/rebuild embeddings (requires embeddings optional deps)
- `--embedding-model TEXT`: Embedding model name (default: `sentence-transformers/all-MiniLM-L6-v2`)

**Existing Options (unchanged)**

- `--limit, -n INT`: Max results (default: `10`)
- `--problem, -p INT`: Filter to specific problem
- `--build-index`: Rebuild index before search

**Global flags**

- `--json` is a **global** flag (see `src/erdos/cli.py`) and must be supported.
- `--log-level` is a **global** flag (see `src/erdos/cli.py`).

**Mode selection and validation**

- Mode flags are mutually exclusive: at most one of `--semantic`, `--hybrid`, `--bm25-only`.
- If multiple mode flags are provided, treat this as a usage error (exit nonzero with a clear message).
- `--alpha` is only valid with `--hybrid` (otherwise usage error).
- Default when no mode flag is provided: BM25-only (v1 behavior). Use `--hybrid` or `--semantic` to enable embeddings.

### Examples

```bash
# BM25 search (existing behavior)
uv run erdos search "prime arithmetic progression"

# Semantic search only
uv run erdos search "prime gaps" --semantic

# Hybrid search (combines both)
uv run erdos search "consecutive primes" --hybrid --alpha 0.6

# Build index + embeddings, then search (both flags are additive)
uv run erdos search "prime gaps" --build-index --build-embeddings
uv run erdos search "prime gaps" --semantic
```

---

## 2) Embedding Model Selection

### Default Model

**`sentence-transformers/all-MiniLM-L6-v2`** via `sentence-transformers`

- 384 dimensions
- Fast inference (CPU-friendly)
- Good general-purpose performance
- `sentence-transformers` is Apache-2.0 (model licenses vary; verify at implementation time)

### Alternative (Scientific Text)

**`allenai/specter2`** - optimized for scientific papers

- 768 dimensions
- Better for math/science content
- Heavier model

**Decision:** Start with MiniLM for speed. Users can override via `--embedding-model` flag or config.

---

## 3) Storage Schema

### SQLite Table Extension

Create a separate embeddings table (preferred; avoids changing the v1 FTS schema).

```sql
CREATE TABLE chunk_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES chunks(id),
    embedding BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Decision:** Separate table for cleaner schema evolution.

### Embedding Format

- Stored as numpy array serialized via `numpy.save()` to bytes
- On load: `numpy.load(BytesIO(blob))`
- Dimension stored in `chunk_embeddings.dimension` for validation

---

## 4) Hybrid Ranking Algorithm

### Score Combination

```
hybrid_score = (1 - alpha) * bm25_score_normalized + alpha * semantic_score
```

Where:
- `bm25_score_normalized` = BM25 score normalized to 0..1 with a guard for empty/degenerate result sets
- `raw_cosine` = dot product of normalized embeddings (range -1..1)
- `semantic_score` = `(raw_cosine + 1) / 2` (range 0..1, stable for mixing with normalized BM25)
- `alpha` = weight parameter (default 0.5)

### Retrieval Strategy

1. Run BM25 query, get top-k * 2 candidates
2. Run vector similarity on same candidates (or full corpus if small)
3. Combine scores using hybrid formula
4. Re-rank and return top-k

**Edge cases**

- If there are no candidates, return an empty result list (no division by zero).
- If BM25 scores are all equal (or all zero), set `bm25_score_normalized = 0` for all candidates.
- Candidate expansion factor (default: `2 * k`) is a configurable heuristic to ensure enough items for re-ranking.

---

## 5) Output Schema (JSON)

Extend existing search output (SSOT: archived Spec 006 JSON schema). Existing fields remain unchanged; additional semantic fields are additive.

```json
{
  "schema_version": 1,
  "command": "erdos search",
  "success": true,
  "data": {
    "query": "prime gaps",
    "mode": "hybrid",
    "alpha": 0.5,
    "limit": 10,
    "count": 5,
    "use_fts": true,
    "results": [
      {
        "chunk_id": "problem_6_statement",
        "problem_id": 6,
        "snippet": "...",
        "score": 12.5,
        "semantic_score": 0.87,
        "hybrid_score": 0.91
      }
    ],
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  }
}
```

---

## 6) Implementation

### 6.1 New Module: `src/erdos/core/embeddings.py`

Responsibilities:

1. Load embedding model (lazy, cached)
2. Generate embeddings for text chunks
3. Serialize/deserialize embeddings for SQLite
4. Compute cosine similarity

```python
# Example API
from erdos.core.embeddings import EmbeddingModel

model = EmbeddingModel("all-MiniLM-L6-v2")
embedding = model.encode("prime arithmetic progression")  # np.ndarray
similarity = model.cosine_similarity(embedding1, embedding2)  # float

# Serialization helpers (SQLite BLOB)
blob = model.to_blob(embedding)  # bytes
roundtripped = model.from_blob(blob)  # np.ndarray
```

### 6.2 Extend: `src/erdos/core/search_index.py`

Add methods:

- `build_embeddings(model_name: str) -> int` - Generate embeddings for all chunks
- `search_semantic(query: str, limit: int) -> list[SearchResult]`
- `search_hybrid(query: str, limit: int, alpha: float) -> list[SearchResult]`

### 6.3 Extend: `src/erdos/core/index_builder.py`

The CLI entry point for index building is `erdos search --build-index` (SSOT: `src/erdos/commands/search.py`), which calls `src/erdos/core/index_builder.py`. Extend the builder to optionally:

- build embeddings when `--build-embeddings` is set, after chunks are indexed
- record the active embedding model name in index metadata

### 6.4 CLI Output (Presenter)

When extending `erdos search`, all output must route through the shared presenter utilities (archived Spec 009) so human/JSON output stays consistent and JSON mode never writes progress messages to stdout.

### 6.5 Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
embeddings = [
    "sentence-transformers>=5.2.0",
    "numpy>=2.4.1",
]
```

**Install (uv):** `uv sync --extra embeddings`

---

## 7) Verification: This Spec is Testable

### Vertical Slice Test

```bash
# Prepare a local data dir (v1 expects enriched YAML with title/statement)
tmp_data="$(mktemp -d)"
cp tests/fixtures/sample_problems.yaml "$tmp_data/problems_enriched.yaml"
export ERDOS_DATA_PATH="$tmp_data"
export ERDOS_INDEX_PATH="$(mktemp -d)/erdos.sqlite"

# Build index (FTS) + embeddings
uv run erdos search "prime gaps" --build-index --build-embeddings

# Semantic search
uv run erdos search "prime gaps" --semantic --json | jq '.data.results[0].semantic_score'
# Should return a float between 0 and 1

# Hybrid search
uv run erdos search "consecutive primes" --hybrid
```

### Unit Tests

- `tests/unit/test_embeddings.py`
  - Model loading and caching
  - Embedding generation produces correct dimensions
  - Cosine similarity computation
  - Serialization roundtrip (numpy → blob → numpy)

### Integration Tests

- `tests/integration/test_search_semantic.py`
  - Build index with embeddings from fixtures
  - Semantic search returns results
  - Hybrid search combines scores correctly
  - `--bm25-only` ignores embeddings

### Acceptance Criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

Note: Tests should mock the embedding model to avoid slow downloads.
Recommended pattern:
- monkeypatch `EmbeddingModel.encode()` to return a small deterministic vector (e.g., all zeros with a fixed dimension)
- avoid network downloads by stubbing any model-loading logic in unit tests

---

## 8) Performance Considerations

### Index Build Time

- Embedding generation is CPU-bound
- ~100 chunks/second on modern CPU with MiniLM
- For 1000+ chunks, show progress bar

### Search Latency

- Brute-force cosine similarity is O(n) where n = corpus size
- Acceptable for < 10,000 chunks
- If scale requires it, add FAISS/hnswlib in future spec

### Memory

- 384-dim float32 embedding = 1.5 KB per chunk
- 10,000 chunks = ~15 MB in memory
- SQLite BLOB storage keeps memory bounded

---

## References

- sentence-transformers: `https://www.sbert.net/`
- SPECTER2: `https://huggingface.co/allenai/specter2`
- Master vision hybrid search: `docs/specs/master-vision.md` (Section 4, Issue 9)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-01-18 | Initial spec |
