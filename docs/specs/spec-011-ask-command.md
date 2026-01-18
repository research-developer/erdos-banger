# Spec 011: Ask Command (RAG Prompt + Optional LLM)

> Adds `erdos ask` for retrieval-augmented Q&A about a specific Erdős problem, with citation-grounded answers.

**Status:** Pending
**Target:** v1.1
**Prerequisites (SSOT):**
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Problem loader: `docs/_archive/specs/spec-005-problem-loader.md`
- CLI patterns: `docs/_archive/specs/spec-004-cli-architecture.md`
- Models: `docs/_archive/specs/spec-003-domain-models.md`

---

## 0) Scope (v1.1)

### In scope

1. Retrieve top-k relevant chunks for `(problem_id, question)` using the existing SQLite FTS5 index.
2. Build a deterministic prompt that includes:
   - the problem statement (and notes when present)
   - numbered sources (retrieved chunks)
   - the user question
3. Optional: run an **external** LLM command (subprocess) to generate an answer.
4. Always return:
   - the retrieved sources
   - the prompt used
   - (if LLM ran) the answer text

### Out of scope

- Direct SDK/API integration with Anthropic/OpenAI (avoid secrets + dependency surface in v1.1)
- Reranking, embeddings, vector search
- “Chat” / multi-turn state

Rationale: v1.1 should work in CI and locally without API keys. Users can opt into LLM calls via a configurable command.

---

## 1) CLI Interface

### Command signature

```text
erdos ask PROBLEM_ID QUESTION [OPTIONS]
```

**Arguments**

- `PROBLEM_ID` (int, required)
- `QUESTION` (string, required)

**Options**

- `--limit, -n INT`: max retrieved chunks (default: `5`)
- `--build-index`: build/rebuild the search index before retrieval (default: `False`)
- `--no-llm`: retrieval + prompt only; do not run an LLM (default: `False`)
- `--llm-cmd TEXT`: override the LLM command to execute (default: from `ERDOS_LLM_COMMAND`)

**Global flags**

- `--json` must be supported (see `src/erdos/cli.py` / Spec 004).

### Examples

```bash
# Prompt-only (no LLM): deterministic and CI-safe
uv run erdos ask 6 "What partial results are known?" --no-llm

# Run LLM via external command (example: a local wrapper script)
ERDOS_LLM_COMMAND="./scripts/llm.sh" uv run erdos ask 6 "Summarize known results"

# Machine output
uv run erdos --json ask 6 "Status?" --no-llm
```

---

## 2) Output Schema (JSON)

All JSON output must be wrapped in `CLIOutput` (Spec 003). `data` must include:

```json
{
  "problem_id": 6,
  "question": "What partial results are known?",
  "prompt": "<full prompt text>",
  "answer": null,
  "sources": [
    {
      "id": 1,
      "chunk_id": "problem_6_statement",
      "source_type": "problem_statement",
      "problem_id": 6,
      "reference_doi": null,
      "text": "..."
    }
  ],
  "retrieval": {
    "query": "Problem 6: <title>. Question: <question>",
    "limit": 5,
    "count": 5,
    "used_fts": true
  },
  "llm": {
    "enabled": false,
    "command": null,
    "exit_code": null
  }
}
```

Notes:

- `answer` is `null` when `--no-llm` is used or no LLM command is configured.
- When LLM is enabled, `llm.exit_code` is required and `answer` must be non-empty on success.
- When `--json` is enabled, no progress/human text may be written to stdout.

---

## 3) Implementation (Modules to Create)

### 3.1 Core logic: `src/erdos/core/ask.py`

Responsibilities:

1. Load problem via `ProblemLoader.from_default()` + `get_by_id()`.
2. Ensure a usable index:
   - If `--build-index`, call `erdos.core.index_builder.build_index(rebuild=True)`.
   - Else use `SearchIndex.from_default()` and proceed even if empty (returns zero results).
3. Retrieval:
   - Call `SearchIndex.search(query, limit=limit, problem_id=problem_id)` to bias towards the selected problem.
   - If FTS index is empty, fall back to a basic search over `problem.statement` + `problem.notes` and return “used_fts=false”.
4. Prompt construction:
   - Deterministic format with numbered sources.
5. Optional LLM execution:
   - If `--no-llm` is false and an LLM command is configured, execute it via `subprocess.run`.
   - Provide the prompt via stdin.
   - Capture stdout as the answer.
6. Return `CLIOutput.ok(command="erdos ask", data=...)` on success; `CLIOutput.err(...)` on failures.

### 3.2 CLI command: `src/erdos/commands/ask.py`

- Follow the command-module pattern (Spec 004).
- Output via the shared presenter helpers (`exit_with_result` from `erdos.commands.presenter`).
- Exit codes:
  - Unknown problem id → `ExitCode.NOT_FOUND`
  - Index build failure → `ExitCode.ERROR`
  - LLM command configured but fails (non-zero exit) → `ExitCode.ERROR`

---

## 4) Prompt Format (SSOT)

The prompt must be deterministic (same inputs → same prompt) to support regression testing.

### Prompt template

```text
You are assisting with research on a specific Erdős problem.

Problem:
- id: {problem_id}
- title: {title}

Statement:
{statement}

Notes:
{notes_or_empty}

Sources (cite as [n]):
[1] ({source_type}) {chunk_id}
{chunk_text}

[2] ...

Question:
{question}

Instructions:
- Answer using only the sources above.
- When making a claim, cite the supporting source like [1] or [2].
- If the sources are insufficient, say so explicitly and suggest what to ingest/search next.
```

---

## 5) Verification: This Spec is Testable

### Unit tests (no LLM, no network)

- `tests/unit/test_ask_prompt.py`
  - Prompt includes statement, question, and numbered sources.
  - Prompt is stable (exact string match) given fixed inputs.

### Integration tests (no network; LLM mocked)

- `tests/integration/test_cli_ask.py`
  - Build an index from `tests/fixtures/sample_problems.yaml` (or use an in-memory SearchIndex fixture if available).
  - Run `erdos ask 6 "prime" --no-llm --json` and assert:
    - stdout is valid JSON (`CLIOutput`)
    - `data.answer is null`
    - `data.sources` is non-empty
  - Run with a fake LLM command (e.g., a small Python one-liner that echoes stdin) and assert:
    - `data.answer` is non-empty
    - `llm.enabled=true` and `llm.exit_code=0`

### Acceptance criteria

```bash
uv run ruff check .
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

---

## References

- SQLite FTS5 (built-in via `sqlite3`): `https://www.sqlite.org/fts5.html`
- subprocess execution (Python): `https://docs.python.org/3/library/subprocess.html`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.2.0 | 2026-01-18 | Rewrite: align with v1 `src/erdos/core` structure; external LLM via subprocess (no SDK/API deps) |
