# Spec 025: Index Research Artifacts into Search DB

> Makes research state usable by retrieval by indexing curated research artifacts into `index/erdos.sqlite` and including synthesis in `erdos ask` / `erdos loop` context.

**Status:** Archived
**Target:** v3.0
**Prerequisites (SSOT):**
- Research workspace: `docs/_archive/specs/spec-023-research-workspace.md`
- Research records: `docs/_archive/specs/spec-024-research-records.md`
- Search index: `docs/_archive/specs/spec-006-search-index.md`
- Ask command: `docs/_archive/specs/spec-011-ask-command.md`

---

## 0) Scope (v3.0)

### In scope

1) Add new `ChunkSource` values for research artifacts:
   - `research_synthesis`
   - `research_lead`
   - `research_attempt`
   - `research_hypothesis`
   - `research_task`
2) Extend index build (`erdos search --build-index`) to index:
   - `SYNTHESIS.md`
   - rendered lead/attempt/hypothesis/task records (YAML → deterministic text)
3) Ensure indexed research chunks set `problem_id` for filtering.
4) Update `erdos ask` retrieval to always include `SYNTHESIS.md` when present (as a baseline source), even if the index is empty.

### Out of scope

- Indexing raw `SCRATCHPAD.md` text (too noisy) — explicitly excluded for v3.
- Any new database schema migrations (SQLite schema remains unchanged).

---

## 1) Chunk IDs + Rendering (authoritative)

### Chunk IDs

- Synthesis: `research_{problem_id}_synthesis`
- Record file: `research_{problem_id}_{record_id}`
  - Example: `research_6_lead_20260123T000501Z_a1b2c3`

### Rendering rules (deterministic)

Each YAML record is rendered to a single plain-text chunk:

```text
Kind: lead
ID: lead_...
Problem: 6
Title: ...
Status: ...
Priority: ...
Source: doi=... arxiv_id=... url=...
Notes:
...
```

The exact fields depend on record kind, but the format must be:
- stable ordering
- stable labels
- no timestamps except when necessary for identification (`created_at`, `updated_at`)

---

## 2) CLI Behavior Changes

### `erdos search --build-index`

Building/rebuilding the index must include both:
- problem statement + problem notes (existing)
- research artifacts (new)

### `erdos ask`

When `research/problems/{id}/SYNTHESIS.md` exists:
- It must be included as a source in the built prompt (source_type=`research_synthesis`).
- This inclusion must happen even if the SQLite index has zero chunks.

No new CLI flags are introduced in v3.

---

## 3) Output Schema (JSON)

### Search

`erdos search` result payload already includes `source_type` and snippet/text. Research chunks will appear with the new `source_type` values.

### Ask

`erdos ask` result payload already returns `sources[]`. Research synthesis must appear as one of the sources when present.

---

## 4) Implementation (modules / wiring)

### Update core models

- `src/erdos/core/models/search.py`
  - Extend `ChunkSource` enum with research values.

### Extend index building

- `src/erdos/core/search/indexing_service.py`
  - Call research indexing best-effort after `build_index(...)`.
- `src/erdos/core/search/research_indexing.py`
  - Scan the `research/` workspace and index curated artifacts.
- `src/erdos/commands/search.py`
  - Pass `repo_root` from `AppConfig` into index building (no env reads in core).

### Add research→chunk renderer

- `src/erdos/core/research/render.py`
  - Deterministic render functions: `render_lead(record) -> str`, etc.
  - `render_synthesis(markdown) -> str` (may be identity).

### Ask integration

- `src/erdos/core/ask/retrieval.py`
  - Add `SYNTHESIS.md` as a baseline source when present.
  - Avoid duplicating if it is also retrieved from FTS (dedupe by `chunk_id`).

---

## 5) Verification (TDD; testable claims)

### Unit tests

1) Enum roundtrip:
   - `ChunkSource("research_synthesis")` parses successfully.
2) Renderer determinism:
   - Same record renders to identical string across runs.

### Integration tests

1) Research artifacts are searchable:
   - Create workspace + add a lead with unique text.
   - Run `erdos --json search "unique text" --build-index --problem 6`.
   - Assert results include `source_type` = `research_lead`.
2) Ask includes synthesis baseline:
   - Create `SYNTHESIS.md` with a unique marker string.
   - Run `erdos --json ask 6 "question" --no-llm` without building index.
   - Assert `sources[]` contains one entry with `source_type` = `research_synthesis` and includes the marker text.

All integration tests must set:
- `ERDOS_DATA_PATH`
- `ERDOS_INDEX_PATH` (tmp sqlite path)
- `ERDOS_REPO_ROOT` (tmp workspace root)

---

## 6) Changelog

- v1 (Complete): Index curated research artifacts + include synthesis in ask.
