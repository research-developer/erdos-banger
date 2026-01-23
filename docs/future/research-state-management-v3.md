# Research State Management (v3) — Notes, Leads, Attempts, and “Campaign Memory”

> **Document Status:** Implemented (pending senior review)
>
> **Last Updated:** 2026-01-23
>
> **Verification:** `pytest -m "not requires_lean and not requires_network"`
>
> **Goal:** Add a durable, navigable “research workspace” layer so humans + agents can iteratively collect sources, take notes, track leads/attempts, and feed the right context into `erdos ask` / `erdos loop run` without relying on the Ralph Wiggum *code-development* loop.

---

## Decision summary (locked for v3)

This is the exact architecture we will build first:

- **Canonical research state (SSOT):** a git-tracked `research/` directory with per-problem folders and a small set of standard files (Markdown + YAML).
- **Merge-safe structure:** structured items are stored as **one YAML file per record** (e.g., `leads/lead_*.yaml`, `attempts/att_*.yaml`) to avoid “giant YAML list” merge conflicts.
- **No extra event log:** no `activity.jsonl` in v3; Git history is the audit trail.
- **No sessions:** no session model in v3; campaign = per-problem folder.
- **Synthesis-first retrieval:** `SYNTHESIS.md` is always included in `erdos ask` / `erdos loop run` context when present.
- **Index curated research:** index `SYNTHESIS.md` **and** rendered structured records (leads/attempts/hypotheses/tasks) into SQLite; do **not** index raw scratchpad text.
- **Deterministic synthesis:** v3 does not allow an LLM to write canonical `SYNTHESIS.md`.
- **Implementation order:** SPEC-023 → SPEC-024 → SPEC-025 → SPEC-026 → SPEC-027.

Implementation pointers:

- Specs: `docs/_archive/specs/spec-023-research-workspace.md` → `docs/_archive/specs/spec-027-loop-research-integration.md`
- CLI entrypoints: `src/erdos/commands/research/__init__.py`, `src/erdos/commands/ask.py`, `src/erdos/commands/loop.py`
- Core logic: `src/erdos/core/research/`, `src/erdos/core/ask/retrieval.py`, `src/erdos/core/search/research_indexing.py`

Non-goals for v3 (explicitly not building):

- database-as-SSOT research state
- event-sourcing/replay systems
- monolithic per-problem “one big YAML list” state files (merge pain)
- indexing full scratchpad text into RAG (too noisy)
- cross-problem knowledge graphs
- vendor memory products as the canonical store

---

## 0) Why This Exists (and what it is *not*)

### Ralph vs research

- `logs/ralph/` is **only** for the Ralph Wiggum *autonomous codebase-building* sprint loop (`scripts/ralph-loop.sh`).
- Mathematical research/proof work currently produces:
  - run summaries in `logs/runs.jsonl` (command-level logging)
  - proof-loop iteration logs in `logs/loop/*.jsonl`
  - literature manifests in `literature/manifests/*.yaml` and caches in `literature/cache/` (gitignored)

### The missing layer

Pre-v3 we lacked a first-class system for:

- multi-day “campaign” work on a problem (days/weeks)
- scratchpad notes + structured lead tracking + attempt outcomes
- durable synthesis that can be fed back into RAG + Lean loop
- a clear, standardized place for humans/agents to write/read state

v3 implements that missing layer via the repo-local `research/` workspace (see “Decision summary” above).

---

## 1) Current Stack Reality (today)

What exists already (relevant to this design):

- **Search/RAG index DB:** `index/erdos.sqlite` (SQLite + FTS5 + optional embeddings).
  - `erdos search` queries it.
  - `erdos ask` retrieves chunks from it and builds a deterministic citation prompt.
  - Today it indexes problem statements + `ProblemRecord.notes` **and** (best-effort) curated research artifacts:
    - `research/problems/*/SYNTHESIS.md`
    - rendered structured records: leads/attempts/hypotheses/tasks
  - It does **not** index `SCRATCHPAD.md` (too noisy) and does **not** index raw literature extracts by default.
- **Literature ingestion:** manifests in `literature/manifests/{problem_id:04d}.yaml`, content cached/extracted under `literature/cache/` and `literature/extracts/` (gitignored).
- **Proof loop:** `erdos loop run` generates/patches Lean code and writes detailed JSONL iteration logs under `logs/loop/`.

What still does **not** exist (by design in v3):

- sessions/threads as first-class entities (campaign = per-problem folder)
- an event-sourced activity log (Git history is the audit trail)
- LLM-written canonical `SYNTHESIS.md` (synthesis is deterministic)
- indexing full scratchpad text into RAG (too noisy)

---

## 2) 2026 Patterns Worth Copying (translated into our world)

These are proven patterns we can adopt without importing a heavyweight framework:

1) **Persistent “threads/sessions” + checkpointing**
   - Many agent frameworks persist state by “thread id” with resumable checkpoints.
   - Translation: treat each problem’s campaign as a durable “thread” with a stable ID and resumable state.

2) **Small durable memory + large external memory**
   - Keep a *small* always-available summary (“memory blocks”), while using RAG for the long tail.
   - Translation:
     - `SYNTHESIS.md` = small, curated, always-included context
     - search index (`index/erdos.sqlite`) + literature extracts = external memory

3) **Event log / append-only truth for auditability**
   - Event sourcing stores “what happened” and derives state from events.
   - Translation: use Git history as the append-only audit trail for canonical research artifacts; do **not** introduce a separate event log in v3.

4) **File-based “memory directories”**
   - A practical approach for agents is “memory as files you can CRUD”.
   - Translation: a standard `research/` folder layout that agents can safely read/write, without DB migrations.

---

## 2.5) 2025/2026 ecosystem survey (what’s out there)

This section is **non-normative background** only. The v3 implementation does not depend on any of these tools/libraries; treat links as pointers to review separately.

This is a non-exhaustive shortlist of patterns and tooling that show up repeatedly in 2025–2026 agent systems. The point is not to adopt everything; it’s to steal the *right* ideas for our constraints (CLI-first, repo-local, reproducible, auditable, multi-session research).

### A) Agent/session orchestration + checkpointing (state over time)

- **LangGraph persistence / checkpointers**
    - Pattern: “thread id” + persisted checkpoints (SQLite/Postgres/Redis) so a workflow can resume and “time travel” to prior states.
  - Sources:
    - <https://langchain-ai.github.io/langgraph/how-tos/persistence/>
    - <https://langchain-ai.github.io/langgraphjs/how-tos/persistence/>

- **OpenAI Agents SDK sessions**
  - Pattern: explicit session objects for agent runs; store/restore context and tool outputs.
  - Sources:
    - <https://openai.github.io/openai-agents-python/sessions/>
    - <https://openai.github.io/openai-agents-js/guides/sessions/>

- **LlamaIndex Workflows state management**
  - Pattern: workflow graphs with explicit persisted state and resumability.
  - Source:
    - <https://docs.llamaindex.ai/en/stable/module_guides/workflow/state/>

### B) “Memory” layers (episodic notes + durable summaries)

- **File-based memory tool (Anthropic)**
  - Pattern: store durable “memories” outside the ephemeral chat context (CRUD-able).
  - Source:
    - <https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool>

- **Explicit memory blocks (Letta)**
  - Pattern: separate memory into explicit blocks and treat them as first-class objects.
  - Source:
    - <https://docs.letta.com/concepts/memory-blocks>

- **Memory services (mem0, Zep)**
  - Pattern: durable store of “facts/episodes” + retrieval/updates across runs.
  - Sources:
    - <https://docs.mem0.ai/overview>
    - <https://docs.getzep.com/>

- **Microsoft ecosystem (Agent Framework / AutoGen / Semantic Kernel)**
  - Pattern: memory as a pluggable component with explicit storage backends.
  - Sources:
    - <https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/agent-framework/overview>
    - <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/memory.html>
    - <https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-memory?pivots=programming-language-python>

### C) Durable execution / workflow engines (production-grade robustness)

If we ever want “run this campaign for 6 hours, survive crashes, retry safely, resume tomorrow”, the mature answer is **durable workflow execution**.

- **Temporal**
  - Pattern: workflows with persisted state and replayable execution history (“durable execution”).
  - Sources:
    - <https://docs.temporal.io/>
    - <https://docs.temporal.io/dev-guide/python>

### D) Vector search / retrieval infra (local-first vs production)

We already have SQLite + FTS5. For semantic search, common 2025–2026 options:

- **Stay local:** SQLite + vector extension
  - <https://github.com/asg017/sqlite-vec>
  - <https://github.com/asg017/sqlite-vss>
- **Production default:** Postgres + pgvector
  - <https://github.com/pgvector/pgvector>

---

## 3) Storage Options (at least three) + tradeoffs

### Option A — **Git-tracked file workspace (Markdown + YAML)**

**Idea:** `research/` is the canonical workspace. Humans/agents edit text files directly. Git is the time machine.

- **Pros**
  - human-first and agent-first (simple read/write)
  - diffable, reviewable, mergeable (especially YAML/Markdown)
  - no migrations, no ORM, no new infra
  - works offline and survives tool changes
- **Cons**
  - structured queries require parsing YAML
  - without conventions/templates, notes can drift

### Option B — **SQLite as primary (normalized tables + FTS5)**

**Idea:** build a dedicated research DB (tables for sessions/notes/leads/attempts), optionally with FTS5 for notes.

- **Pros**
  - great queryability (“show me all dead_end leads for problem 6”)
  - strong invariants, easy joins, atomic writes
  - easy to add derived views (“current_state”)
- **Cons**
  - binary diffs (hard to code review, painful merges)
  - versioning/migrations become a thing (even if lightweight)
  - humans don’t naturally “edit a database”

### Option C — **Hybrid: event log + Markdown projections**

**Idea:** append-only event log is the “truth” (text JSONL or similar); Markdown/YAML projections are generated/updated by CLI.

- **Pros**
  - full audit trail + easy “time travel”
  - derived docs are regenerable and standardized
  - scalable: can add projections (dashboards, stats) later
- **Cons**
  - more engineering than Option A
  - you must decide what is editable by hand vs derived

### Option D — **External agent-memory products/frameworks**

Examples (not endorsing; just acknowledging the landscape):

- agent/session orchestration with checkpointing (LangGraph, OpenAI Agents SDK, LlamaIndex Workflows)
- memory tool / memory service layers (Anthropic memory tool, Letta memory blocks, mem0, Zep)
- “agent frameworks” with pluggable memory backends (AutoGen, Semantic Kernel, Microsoft Agent Framework)
- durable workflow engines (Temporal) for long-running, restart-safe runs

- **Pros**
  - fastest to “get something working”
  - offloads memory design + persistence
- **Cons**
  - vendor lock-in + network dependency
  - harder to make reproducible/auditable for math research
  - unclear long-term fit for a CLI-first, repo-local workflow

---

## 4) Recommendation: the “perfect stack” for erdos-banger (v3)

### 4.0 The robust choice (clearly marked)

**RECOMMENDED (for erdos-banger as of 2026-01-23):**

- **Canonical SSOT:** repo-local, git-tracked `research/` workspace (Markdown + YAML).
- **Audit trail:** Git history is the audit trail for research state; we do **not** introduce an additional per-problem event log in v3.
- **Derived retrieval index:** keep using `index/erdos.sqlite` (FTS5 + optional embeddings) as *derived* search/RAG memory.
- **Orchestration (near-term):** CLI-first, deterministic commands + structured state; keep agents swappable.
- **Orchestration (future “enterprise mode”):** if we want restart-safe long-running campaigns, add Temporal workflows that run `erdos` operations durably.

This is “robust” in the way research tooling must be robust: reproducible, auditable, local-first, mergeable, and not locked to one vendor’s memory product.

### 4.0.1 Why not make a database the SSOT?

SQLite-as-SSOT (Option B) *is* workable, but it’s a worse daily workflow for humans and code review. Our repo already treats text artifacts as canonical (specs, manifests) and derived databases/logs as regenerable. We should keep that rule.

### 4.0.2 Where Codex CLI / Claude Code fit (no-API-key mode)

We should assume two legitimate workflows will coexist:

1) **Human-in-the-loop, no API keys**
   - The “agent” is you + Codex CLI / Claude Code operating on the repo.
   - `erdos research ...` provides the shared workspace + structure.
   - `erdos ask` / `erdos loop run` can still run in prompt-only mode when LLM isn’t configured.

2) **Automated runs, API-backed**
   - `erdos ask` / `erdos loop run` will continue to use the existing external command interface (`ERDOS_LLM_COMMAND`).
   - If you want provider APIs, run them behind that command (wrapper script or local service) so the core stays vendor-neutral.
   - The key is: whichever LLM is used, it writes back into the same canonical `research/` workspace.

In both cases, the research state layer stays stable and tool-agnostic.

### 4.0.3 The three “full stacks” we could run (and why we pick one)

**Stack 1 (Recommended): Repo-local workspace + derived SQLite (today + v3)**

- Canonical: `research/` (Markdown/YAML)
- Retrieval: `index/erdos.sqlite` (FTS5 + embeddings optional)
- Orchestration: `erdos` CLI commands (+ MCP server as an interface for external agents)
- LLM: external command interface (`ERDOS_LLM_COMMAND`) only; provider APIs live behind a wrapper.

**Stack 2 (Agent-graph native): LangGraph checkpointer + repo workspace**

- Canonical: still `research/` for human visibility
- Orchestration: LangGraph graph for “campaign runs” with checkpointing (SQLite/Postgres/Redis)
- Retrieval: same SQLite index or a dedicated store
- Notes: write-through to `research/` to keep it human/auditable

**Stack 3 (Most robust at scale): Temporal durable workflows + Postgres (+ pgvector)**

- Canonical: `research/` still exists, but primary operational state is in Temporal history + DB tables
- Orchestration: Temporal workflows (retries, resumability, long-running jobs)
- Storage: Postgres for research entities; pgvector for embeddings
- Artifacts: object store (S3/GCS) for large blobs; repo contains only manifests + curated notes

**Decision:** implement Stack 1 now. Keep Stack 2/3 as a paved path once we’ve proven what “good research state” looks like for real problems.

---

**Pick:** Stack 1 (Option A + best of Option C), while continuing to treat SQLite as a **derived** search/index layer.

This matches our repo’s existing philosophy:

- primary artifacts as text (docs/specs, manifests)
- derived stores as regenerable (SQLite index, caches, logs)
- SRP/DIP-friendly: storage is a port with a default filesystem adapter

### 4.1 Canonical artifacts (human + agent workspace)

Add a **git-tracked** directory:

```text
research/
  VERSION
  problems/
    0006/
      meta.yaml
      README.md
      SCRATCHPAD.md
      SYNTHESIS.md
      leads/
        lead_20260123T000501Z_a1b2c3.yaml
      attempts/
        att_20260123T010203Z_ab12cd.yaml
      hypotheses/
        hyp_20260123T001000Z_d4e5f6.yaml
      tasks/
        task_20260123T002000Z_f00baa.yaml
  global/
    TECHNIQUES.md
    GLOSSARY.md
```

**Rules:**

- Markdown files are for free-form, human-readable thinking.
- YAML files are for structured items we must query/update deterministically.
- Structured items are **one-record-per-file** (no giant YAML lists).
- Git is the audit trail for research state (reviewable diffs, blameable changes).
- Never write secrets, tokens, or raw API responses into `research/`.
- The existing “big text” stays gitignored:
  - literature extracts in `literature/extracts/`
  - loop logs in `logs/loop/`
  - search index in `index/`

### 4.2 Navigation UX (how humans + agents will use it)

Primary entrypoints:

- `erdos research init 6` → creates the folder + templates for Problem 6
- `erdos research open 6` → prints the path
- `erdos research note 6 "..."` → appends to `SCRATCHPAD.md`
- `erdos research lead add 6 --title "..." [--doi ...|--arxiv-id ...|--url ...] [--priority high] [--notes "..."]` → writes a new file under `leads/`
- `erdos research attempt log 6 --result failed --summary "..." [--lean-file ...] [--loop-run-log logs/loop/...jsonl]` → writes a new file under `attempts/`
- `erdos research hypothesis add 6 --statement "..."` → writes a new file under `hypotheses/`
- `erdos research task add 6 --title "..." [--priority high]` → writes a new file under `tasks/`
- `erdos research status 6` → prints file presence + record counts (v3; minimal dashboard)
- `erdos research synthesize 6` → updates `SYNTHESIS.md` deterministically (no LLM) from scratchpad + records
- `erdos research fmt 6` → rewrites YAML records into canonical formatting
- `erdos research validate 6` → validates all YAML records against schemas + invariants

### 4.3 RAG integration (so notes actually help)

Add indexing of research artifacts into `index/erdos.sqlite` as additional chunks.

Minimal behavior (v3):

- Extend `erdos search --build-index` to index:
  - `research/problems/{id}/SYNTHESIS.md` → `source_type=research_synthesis`
  - each `research/problems/{id}/leads/lead_*.yaml` rendered to text → `source_type=research_lead`
  - each `research/problems/{id}/attempts/att_*.yaml` rendered to text → `source_type=research_attempt`
  - each `research/problems/{id}/hypotheses/hyp_*.yaml` rendered to text → `source_type=research_hypothesis`
  - each `research/problems/{id}/tasks/task_*.yaml` rendered to text → `source_type=research_task`
- Do **not** index `SCRATCHPAD.md` in v3 (too noisy).

Then:

- `erdos ask` always includes `SYNTHESIS.md` in the prompt when present (baseline source, not “best-effort retrieval”)
- `erdos loop run` always includes `SYNTHESIS.md` in the loop prompt context when present

### 4.4 Loop integration (closing the iteration loop)

When `erdos loop run` runs:

- it already emits detailed logs under `logs/loop/`
- v3 should also emit a single structured “attempt record” into:
  - `research/problems/{id}/attempts/att_*.yaml`

This converts raw logs into *navigable state*.

---

## 5) Data contracts (explicit, so nothing is underspecified)

### 5.1 `research/VERSION` (workspace major version)

Single line:

```text
1
```

This is used to coordinate future migrations across the `research/` workspace.

### 5.2 `meta.yaml` (problem-level metadata)

```yaml
schema_version: 1
problem_id: 6
created_at: "2026-01-23T00:00:00Z"
updated_at: "2026-01-23T00:00:00Z"
```

### 5.3 Lead record: `leads/lead_*.yaml` (one record per file)

```yaml
schema_version: 1
problem_id: 6
id: lead_20260123T000501Z_a1b2c3
title: "Green–Tao theorem"
status: new                 # new | investigating | promising | dead_end | incorporated
priority: high              # low | medium | high
tags: []
source:
  doi: "10.4007/annals.2008.167.481"
  arxiv_id: "math/0404188"
  url: null
notes: "Seems directly relevant; map to the problem statement."
created_at: "2026-01-23T00:05:01Z"
updated_at: "2026-01-23T00:05:01Z"
```

### 5.4 Attempt record: `attempts/att_*.yaml` (one record per file)

```yaml
schema_version: 1
problem_id: 6
id: att_20260123T010203Z_ab12cd
kind: lean_loop            # lean_loop | manual
result: failed             # failed | partial | success
summary: "Stuck on lemma X; induction hypothesis too weak."
artifacts:
  lean_file: "formal/lean/Erdos/Problem006.lean"
  loop_run_log: "logs/loop/run_20260123_010203_ab12cd.jsonl"
created_at: "2026-01-23T01:02:03Z"
```

### 5.5 Hypothesis record: `hypotheses/hyp_*.yaml` (one record per file)

```yaml
schema_version: 1
problem_id: 6
id: hyp_20260123T001000Z_d4e5f6
statement: "Conjecture: ..."
status: active              # active | refuted | proven | incorporated
confidence: medium          # low | medium | high
evidence: []
notes: ""
created_at: "2026-01-23T00:10:00Z"
updated_at: "2026-01-23T00:10:00Z"
```

### 5.6 Task record: `tasks/task_*.yaml` (one record per file)

```yaml
schema_version: 1
problem_id: 6
id: task_20260123T002000Z_f00baa
title: "Extract exact lemma statement needed for step X"
status: todo                # todo | doing | blocked | done
priority: high              # low | medium | high
blocked_on: []
links: []
created_at: "2026-01-23T00:20:00Z"
updated_at: "2026-01-23T00:20:00Z"
```

### 5.7 `SCRATCHPAD.md` (free-form, but standardized)

`SCRATCHPAD.md` is where day-to-day thinking goes. To keep it agent-friendly and mergeable, we standardize only the timestamp header. The body is free-form (it is exactly what you pass to `erdos research note`).

```md
# Scratchpad

## 2026-01-23T18:12:00Z

Tried approach X; stuck at lemma Y.
- Next: look up lemma Y in Mathlib
- Question: is there a known reduction to Z?

## 2026-01-23T19:45:00Z

Lead: Paper Z looks promising; extract the exact statement.
```

Rules:

- New entries are appended to the end of the file.
- Each entry begins with an ISO timestamp header (`## ...Z`).
- The note body is not reflowed/rewritten by the CLI (append-only).
- No secrets, tokens, or raw API responses are allowed in this file.

### 5.8 `SYNTHESIS.md` (curated, indexable, always safe to feed to RAG)

`SYNTHESIS.md` is the single curated artifact we feed back into retrieval.

```md
# Synthesis: Problem 0006
_Last updated: 2026-01-23_

## Summary
- ...

## Top tasks (by priority)
- ...

## Active hypotheses
- ...

## Key leads (by priority)
- ...

## Recent attempts (most recent first)
- ...

## Notes (recent scratchpad excerpts)
- ...
```

---

## 6) Implementation slices (what to build first)

### Slice 1 — Workspace + templates + minimal CLI (SPEC-023)

- create `erdos research init/open/note/status`
- define the file layout + template creation
- keep it purely file-based (no DB)

### Slice 2 — Structured records CRUD (SPEC-024)

- implement CRUD for `lead`, `attempt`, `hypothesis`, `task`
- guarantee stable IDs and schema_version checks (one-record-per-file)
- implement `erdos research fmt` (canonical YAML) and `erdos research validate` (schema validation)

### Slice 3 — Index research into the existing search DB (SPEC-025)

- extend indexing so `erdos ask` can retrieve **SYNTHESIS + structured records** as first-class chunk sources

### Slice 4 — Deterministic synthesis + loop integration (SPEC-026 / SPEC-027)

- `erdos research synthesize` updates `SYNTHESIS.md` deterministically
- after `erdos loop run`, automatically write an attempt record under `attempts/att_*.yaml`

---

## 7) Proposed Specs (post-review)

Next spec ID is **SPEC-023**. Suggested breakdown:

- **SPEC-023: Research Workspace (Filesystem SSOT)**
  - folder layout + templates, CLI `research init/open/note/status`
- **SPEC-024: Research Records (Structured Tracking)**
  - one-record-per-file CRUD for leads/attempts/hypotheses/tasks + fmt/validate
- **SPEC-025: Index Research Artifacts into Search DB**
  - new chunk sources (`research_synthesis`, `research_lead`, `research_attempt`, `research_hypothesis`, `research_task`)
  - indexing rules + ask retrieval behavior
- **SPEC-026: Deterministic Research Synthesis**
  - deterministic `SYNTHESIS.md` rendering rules and update semantics
- **SPEC-027: Loop → Research Integration**
  - append attempt records after `erdos loop run`, include synthesis in loop prompt context

---

## 8) Decisions (locked for v3; no optionality)

1) `research/` is **git-tracked by default**. This is the canonical authored research state.
2) Structured records are **one-record-per-file** under `leads/`, `attempts/`, `hypotheses/`, `tasks/`.
3) We do **not** implement `activity.jsonl` in v3. Git is the audit trail; `logs/*` remain derived/debug artifacts.
4) We do **not** introduce first-class “sessions” in v3. Campaign = the per-problem folder.
5) We index `SYNTHESIS.md` **and** rendered structured records into SQLite. We do **not** index `SCRATCHPAD.md` in v3 (too noisy).
6) `SYNTHESIS.md` is **deterministic** (no LLM writes to canonical synthesis in v3).
7) `erdos loop run` will write a structured attempt record under `attempts/att_*.yaml` (SPEC-027).
8) Cross-problem knowledge graphs are out of scope until after this layer proves itself on real problems.

---

## 9) References (web, 2025–2026)

- LangGraph persistence (Python): <https://langchain-ai.github.io/langgraph/how-tos/persistence/>
- LangGraph persistence (JS): <https://langchain-ai.github.io/langgraphjs/how-tos/persistence/>
- OpenAI Agents SDK sessions (Python): <https://openai.github.io/openai-agents-python/sessions/>
- OpenAI Agents SDK sessions (JS): <https://openai.github.io/openai-agents-js/guides/sessions/>
- Anthropic memory tool: <https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool>
- Letta memory blocks: <https://docs.letta.com/concepts/memory-blocks>
- mem0 overview: <https://docs.mem0.ai/overview>
- Zep docs: <https://docs.getzep.com/>
- Microsoft Agent Framework overview: <https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/agent-framework/overview>
- AutoGen memory: <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/memory.html>
- Semantic Kernel agent memory: <https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-memory?pivots=programming-language-python>
- LlamaIndex Workflows state: <https://docs.llamaindex.ai/en/stable/module_guides/workflow/state/>
- Temporal docs: <https://docs.temporal.io/>
- Temporal Python dev guide: <https://docs.temporal.io/dev-guide/python>
- sqlite-vec: <https://github.com/asg017/sqlite-vec>
- sqlite-vss: <https://github.com/asg017/sqlite-vss>
- pgvector: <https://github.com/pgvector/pgvector>
