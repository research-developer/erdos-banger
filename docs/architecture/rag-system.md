# RAG System Architecture

This document describes the Retrieval-Augmented Generation (RAG) system used by `erdos ask` and related commands.

## Overview

RAG combines two steps:

1. **Retrieval**: Find relevant text chunks from the corpus
2. **Generation**: Pass retrieved context to an LLM to generate an answer

```text
User Question
    |
    v
+-------------------+
| Retrieval Layer   |
|   - BM25 (FTS5)   |
|   - Semantic      |
|   - Hybrid        |
+-------------------+
    |
    v
+-------------------+
| Prompt Builder    |
| (citation-grounded|
|  RAG prompt)      |
+-------------------+
    |
    v
+-------------------+
| LLM Generation    |
| (external subprocess)
+-------------------+
    |
    v
Answer with Citations
```

---

## 1. Retrieval Layer

### 1.1 BM25 / Full-Text Search (Always Available)

**Technology**: SQLite FTS5 with BM25 ranking

| Aspect | Details |
|--------|---------|
| Database | `index/erdos.sqlite` (gitignored, rebuildable) |
| Tokenizer | Porter stemmer + unicode61 |
| Ranking | BM25 (built into FTS5) |
| Dependencies | None (SQLite is built into Python) |

**Build the index**:
```bash
uv run erdos search "test" --build-index
```

**How it works**:
1. Text is tokenized and stemmed (e.g., "primes" → "prime")
2. FTS5 creates an inverted index mapping terms → documents
3. BM25 scores documents by term frequency and document length
4. Results are ranked by relevance

**Strengths**: Fast, zero dependencies, exact keyword matching
**Weaknesses**: Misses semantic similarity ("prime gaps" won't find "consecutive primes")

### 1.2 Semantic Search (Optional)

**Technology**: `sentence-transformers` library wrapping Hugging Face models

| Aspect | Details |
|--------|---------|
| Default Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Storage | SQLite BLOB (numpy serialized) |
| Dependencies | `uv sync --extra embeddings` |

**What is `all-MiniLM-L6-v2`?**

- **Open source**: Yes, Apache 2.0 license
- **Source**: [Hugging Face](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- **Based on**: Microsoft's MiniLM (distilled from BERT)
- **Size**: ~80MB download on first use
- **Performance**: CPU-friendly, ~100 embeddings/second

**How sentence-transformers works**:
1. You install: `uv sync --extra embeddings`
2. First use triggers model download from Hugging Face Hub (~80MB)
3. Model is cached in `~/.cache/huggingface/` (or `$HF_HOME`)
4. `SentenceTransformer.encode(text)` → 384-dimensional numpy array
5. Vectors are compared via cosine similarity

**Build embeddings**:
```bash
uv run erdos search "test" --build-index --build-embeddings
```

**Search with semantic mode**:
```bash
uv run erdos search "prime gaps" --semantic
```

### 1.3 Hybrid Search (Best of Both)

Combines BM25 keyword matching with semantic similarity:

```
hybrid_score = (1 - alpha) * bm25_normalized + alpha * semantic_score
```

Where:
- `alpha = 0.5` (default, tunable via `--alpha`)
- `bm25_normalized` = BM25 score scaled to [0, 1]
- `semantic_score` = (cosine_similarity + 1) / 2, scaled to [0, 1]

**Usage**:
```bash
uv run erdos search "consecutive primes" --hybrid --alpha 0.6
```

---

## 2. Ask Command (RAG Orchestration)

The `erdos ask` command orchestrates the full RAG pipeline.

**File**: `src/erdos/core/ask/service.py`

### 2.1 Retrieval Phase

**File**: `src/erdos/core/ask/retrieval.py`

```python
def perform_retrieval(
    index: SearchIndex,
    problem: ProblemRecord,
    question: str,
    limit: int = 5,
) -> list[SearchResult]:
```

1. Builds a safe FTS5 query from problem title + question
2. Extracts alphanumeric tokens, deduplicates, quotes each
3. Joins with `OR` (max 10 terms)
4. Falls back to problem statement/notes if index is empty

**Fallback sources** (when index has no data):
- Research synthesis (`research/{id}/SYNTHESIS.md`)
- Problem statement
- Problem notes

### 2.2 Prompt Construction

**File**: `src/erdos/core/ask/prompt.py`

Builds a structured, citation-grounded prompt:

```text
You are assisting with research on a specific Erdos problem.

Problem:
- id: 6
- title: Prime Arithmetic Progression

Statement:
[Full problem statement]

Notes:
[Problem notes or "(none)"]

Sources (cite as [n]):
[1] (problem_statement) problem_6_statement
[Full text...]

[2] (reference) arxiv_2401.12345
[Retrieved chunk text...]

Question:
What is known about this problem?

Instructions:
- Answer using only the sources above.
- When making a claim, cite the supporting source like [1] or [2].
- If the sources are insufficient, say so explicitly.
```

### 2.3 LLM Execution

**File**: `src/erdos/core/ask/llm.py`

The LLM is **external and configurable** - you bring your own:

| Config Method | Example |
|--------------|---------|
| Flag | `erdos ask 6 "question" --llm-cmd "claude --no-tools"` |
| Environment | `ERDOS_LLM_COMMAND="claude --no-tools"` |

**How it works**:
1. Prompt is passed via stdin to the subprocess
2. Answer is read from stdout
3. Exit code is checked (non-zero = error)
4. Timeout is configurable (default: 60s)

**Example LLM commands**:
```bash
# Claude Code CLI
ERDOS_LLM_COMMAND="claude --no-tools" erdos ask 6 "What progress exists?"

# OpenAI CLI
ERDOS_LLM_COMMAND="openai api chat.completions.create -m gpt-4 ..." erdos ask 6 "..."

# Local model via Ollama
ERDOS_LLM_COMMAND="ollama run llama2" erdos ask 6 "..."
```

---

## 3. Storage Schema

### 3.1 Tables

```sql
-- Problem metadata
CREATE TABLE problems (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    statement TEXT,
    status TEXT,
    prize TEXT,
    tags TEXT  -- JSON array
);

-- Text chunks (indexed content)
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    problem_id INTEGER,
    source_type TEXT,  -- 'problem_statement', 'reference', etc.
    reference_doi TEXT,
    text TEXT NOT NULL
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    chunk_id,
    text,
    content='chunks',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Vector embeddings (optional)
CREATE TABLE chunk_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES chunks(id),
    embedding BLOB NOT NULL,  -- numpy array serialized
    dimension INTEGER NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Schema metadata
CREATE TABLE schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

### 3.2 Embedding Serialization

Embeddings are stored as numpy arrays serialized to bytes:

```python
# Write
buffer = io.BytesIO()
np.save(buffer, embedding)
blob = buffer.getvalue()

# Read
buffer = io.BytesIO(blob)
embedding = np.load(buffer)
```

---

## 4. Configuration

### 4.1 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ERDOS_INDEX_PATH` | SQLite database location | `index/erdos.sqlite` |
| `ERDOS_DATA_PATH` | Problem data YAML | `data/problems_enriched.yaml` |
| `ERDOS_LLM_COMMAND` | External LLM command | None (LLM disabled) |

### 4.2 Optional Dependencies

```bash
# Install embeddings support
uv sync --extra embeddings

# Verify
uv run python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

---

## 5. Key Files

| File | Purpose |
|------|---------|
| `src/erdos/commands/ask.py` | CLI entry point |
| `src/erdos/core/ask/service.py` | RAG orchestration |
| `src/erdos/core/ask/retrieval.py` | Retrieval with fallback |
| `src/erdos/core/ask/prompt.py` | Citation-grounded prompt builder |
| `src/erdos/core/ask/llm.py` | External LLM subprocess execution |
| `src/erdos/core/search/facade.py` | SearchIndex facade |
| `src/erdos/core/search/bm25.py` | BM25/FTS5 implementation |
| `src/erdos/core/search/embeddings.py` | Embedding model wrapper |
| `src/erdos/core/search/embeddings_store.py` | Embedding storage/retrieval |
| `src/erdos/core/search/hybrid.py` | Hybrid scoring algorithm |

---

## 6. Upgrade Paths

### 6.1 Alternative Embedding Models

The system supports any sentence-transformers model:

```bash
# Use SPECTER2 for scientific text (768 dimensions)
uv run erdos search "prime gaps" --build-embeddings --embedding-model "allenai/specter2"

# Use a larger model for better quality
uv run erdos search "..." --build-embeddings --embedding-model "sentence-transformers/all-mpnet-base-v2"
```

**Model comparison**:

| Model | Dimensions | Size | Best For |
|-------|------------|------|----------|
| `all-MiniLM-L6-v2` | 384 | ~80MB | General, fast |
| `all-mpnet-base-v2` | 768 | ~420MB | Higher quality |
| `allenai/specter2` | 768 | ~440MB | Scientific papers |
| `BAAI/bge-small-en-v1.5` | 384 | ~130MB | Balanced |

### 6.2 OpenAI Embeddings

To switch to OpenAI embeddings:

1. **Pros**: Higher quality, no local model download
2. **Cons**: Requires API key, network calls, costs money
3. **Implementation**: Create new `OpenAIEmbeddingModel` class implementing same interface

```python
# Future: src/erdos/core/search/openai_embeddings.py
class OpenAIEmbeddingModel:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI()
        self.model = model

    def encode(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(input=text, model=self.model)
        return np.array(response.data[0].embedding)
```

**Note**: This would require updating `EmbeddingConfig` to support provider selection.

### 6.3 Vector Databases

**Current state**: Brute-force cosine similarity in SQLite (O(n) per query)

**When to consider a vector DB**:
- Corpus > 100,000 chunks
- Query latency > 1 second
- Need approximate nearest neighbor (ANN) for scale

**Options**:

| Vector DB | Hosting | Pros | Cons |
|-----------|---------|------|------|
| FAISS | Local | Fast ANN, no server | In-memory, rebuild on restart |
| Qdrant | Local/Cloud | Full-featured, Rust-fast | Adds complexity |
| Pinecone | Cloud | Managed, scalable | Vendor lock-in, cost |
| pgvector | Postgres | Combined SQL+vector | Requires Postgres |
| Chroma | Local | Simple API, persisted | Less mature |

**Recommendation**: Stick with SQLite for our scale (~1000 problems). Consider FAISS if we add full-text literature (millions of chunks).

### 6.4 Chunking Strategies

Current: Simple text chunks by source (statement, notes, reference)

**Future improvements**:
- Sliding window with overlap
- Semantic chunking (split at sentence boundaries)
- Hierarchical chunking (document → section → paragraph)

---

## 7. Testing

### 7.1 Unit Tests

```bash
uv run pytest tests/unit/test_embeddings.py -v
```

Tests use fake embeddings (deterministic vectors from character counts) to avoid model downloads.

### 7.2 Integration Tests

```bash
# With embeddings extra
uv sync --extra embeddings
uv run pytest tests/integration/test_search_semantic.py -v
```

### 7.3 Manual Verification

```bash
# Build index + embeddings
export ERDOS_DATA_PATH="tests/fixtures/sample_problems.yaml"
export ERDOS_INDEX_PATH="$(mktemp -d)/test.sqlite"
uv run erdos search "prime" --build-index --build-embeddings

# Test different modes
uv run erdos search "prime" --json | jq '.data.results[0].score'
uv run erdos search "prime" --semantic --json | jq '.data.results[0].semantic_score'
uv run erdos search "prime" --hybrid --json | jq '.data.results[0].hybrid_score'
```

---

## 8. Design Decisions

### 8.1 Why SQLite over Vector DBs?

See [ADR-003](../adr/adr-003-sqlite-fts5-search-index.md):
- Local-first, no external services
- Deterministic rebuilds
- Good enough for our scale (~1000 problems)

### 8.2 Why External LLM over Built-in?

- **Flexibility**: Users choose their preferred model/provider
- **Cost control**: No hidden API costs
- **Privacy**: No data sent without explicit configuration
- **Testing**: Easy to mock (just don't set the env var)

### 8.3 Why sentence-transformers over OpenAI?

- **Offline**: Works without internet after initial download
- **Free**: No per-query costs
- **Privacy**: No data leaves your machine
- **Speed**: Local inference is often faster than API calls

---

## Related Documentation

- [ADR-003: SQLite FTS5](../adr/adr-003-sqlite-fts5-search-index.md) - Why SQLite
- [Spec 014: Vector Embeddings](../_archive/specs/spec-014-vector-embeddings.md) - Semantic search implementation
- [Spec 006: Search Index](../_archive/specs/spec-006-search-index.md) - Original FTS5 design
- [Spec 011: Ask Command](../_archive/specs/spec-011-ask-command.md) - Ask command design
