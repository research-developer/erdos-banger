# Research State Management (v3) — Notes, Sessions, and “Campaign Memory”

> **Document Status:** Brainstorming / design proposal for senior review
>
> **Last Updated:** 2026-01-23
>
> **Goal:** Add a durable, navigable “research workspace” layer so humans + agents can iteratively collect sources, take notes, track leads/attempts, and feed the right context into `erdos ask` / `erdos loop` without relying on the Ralph Wiggum *code-development* loop.

---

## 0) Why This Exists (and what it is *not*)

### Ralph vs research

- `logs/ralph/` is **only** for the Ralph Wiggum *autonomous codebase-building* sprint loop (`scripts/ralph-loop.sh`).
- Mathematical research/proof work currently produces:
  - run summaries in `logs/runs.jsonl` (command-level logging)
  - proof-loop iteration logs in `logs/loop/*.jsonl`
  - literature manifests in `literature/manifests/*.yaml` and caches in `literature/cache/` (gitignored)

### The missing layer

We lack a first-class system for:

- multi-session “campaign” work on a problem (days/weeks)
- scratchpad notes + structured lead tracking + attempt outcomes
- durable synthesis that can be fed back into RAG + Lean loop
- a clear, standardized place for humans/agents to write/read state

This doc proposes that missing layer.

---

## 1) Current Stack Reality (today)

What exists already (relevant to this design):

- **Search/RAG index DB:** `index/erdos.sqlite` (SQLite + FTS5 + optional embeddings).
  - `erdos search` queries it.
  - `erdos ask` retrieves chunks from it and builds a deterministic citation prompt.
- **Literature ingestion:** manifests in `literature/manifests/{problem_id:04d}.yaml`, content cached/extracted under `literature/cache/` and `literature/extracts/` (gitignored).
- **Proof loop:** `erdos loop` generates/patches Lean code and writes detailed JSONL iteration logs under `logs/loop/`.

What does **not** exist:

- a per-problem scratchpad + lead/attempt tracking system
- any persistence of “what we tried and why it failed” beyond raw logs
- any indexable, curated “current synthesis” beyond the one `ProblemRecord.notes` blob

---

## 2) 2026 Patterns Worth Copying (translated into our world)

These are proven patterns we can adopt without importing a heavyweight framework:

1) **Persistent “threads/sessions” + checkpointing**
   - Many agent frameworks persist state by “thread id” with resumable checkpoints.
   - Translation: treat each problem’s campaign (and optionally each work session) as a durable “thread” with a stable ID and resumable state.

2) **Small durable memory + large external memory**
   - Keep a *small* always-available summary (“memory blocks”), while using RAG for the long tail.
   - Translation:
     - `SYNTHESIS.md` = small, curated, always-included context
     - search index (`index/erdos.sqlite`) + literature extracts = external memory

3) **Event log / append-only truth for auditability**
   - Event sourcing stores “what happened” and derives state from events.
   - Translation: record key research actions (note added, lead promoted, attempt logged, loop run id) in an append-only stream (text-friendly), while maintaining human-readable working docs.

4) **File-based “memory directories”**
   - A practical approach for agents is “memory as files you can CRUD”.
   - Translation: a standard `research/` folder layout that agents can safely read/write, without DB migrations.

---

## 2.5) 2025/2026 ecosystem survey (what’s out there)

This is a non-exhaustive shortlist of patterns and tooling that show up repeatedly in 2025–2026 agent systems. The point is not to adopt everything; it’s to steal the *right* ideas for our constraints (CLI-first, repo-local, reproducible, auditable, multi-session research).

### A) Agent/session orchestration + checkpointing (state over time)

- **LangGraph persistence / checkpointers**
  - Pattern: “thread id” + persisted checkpoints (SQLite/Postgres/Redis) so a workflow can resume and “time travel” to prior states.
  - Sources:
    - https://langchain-ai.github.io/langgraph/how-tos/persistence/
    - https://langchain-ai.github.io/langgraphjs/how-tos/persistence/

- **OpenAI Agents SDK sessions**
  - Pattern: explicit session objects for agent runs; store/restore context and tool outputs.
  - Sources:
    - https://openai.github.io/openai-agents-python/sessions/
    - https://openai.github.io/openai-agents-js/guides/sessions/

- **LlamaIndex Workflows state management**
  - Pattern: workflow graphs with explicit persisted state and resumability.
  - Source:
    - https://docs.llamaindex.ai/en/stable/module_guides/workflow/state/

### B) “Memory” layers (episodic notes + durable summaries)

- **File-based memory tool (Anthropic)**
  - Pattern: store durable “memories” outside the ephemeral chat context (CRUD-able).
  - Source:
    - https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool

- **Explicit memory blocks (Letta)**
  - Pattern: separate memory into explicit blocks and treat them as first-class objects.
  - Source:
    - https://docs.letta.com/concepts/memory-blocks

- **Memory services (mem0, Zep)**
  - Pattern: durable store of “facts/episodes” + retrieval/updates across runs.
  - Sources:
    - https://docs.mem0.ai/overview
    - https://docs.getzep.com/

- **Microsoft ecosystem (Agent Framework / AutoGen / Semantic Kernel)**
  - Pattern: memory as a pluggable component with explicit storage backends.
  - Sources:
    - https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/agent-framework/overview
    - https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/memory.html
    - https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-memory?pivots=programming-language-python

### C) Durable execution / workflow engines (production-grade robustness)

If we ever want “run this campaign for 6 hours, survive crashes, retry safely, resume tomorrow”, the mature answer is **durable workflow execution**.

- **Temporal**
  - Pattern: workflows with persisted state and replayable execution history (“durable execution”).
  - Sources:
    - https://docs.temporal.io/
    - https://docs.temporal.io/dev-guide/python

### D) Vector search / retrieval infra (local-first vs production)

We already have SQLite + FTS5. For semantic search, common 2025–2026 options:

- **Stay local:** SQLite + vector extension
  - https://github.com/asg017/sqlite-vec
  - https://github.com/asg017/sqlite-vss
- **Production default:** Postgres + pgvector
  - https://github.com/pgvector/pgvector

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
- **Audit trail:** append-only `activity.jsonl` written by `erdos` commands (optional but recommended).
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
   - `erdos ask` / `erdos loop` can still run in prompt-only mode when LLM isn’t configured.

2) **Automated runs, API-backed**
   - `erdos ask` / `erdos loop` can use direct provider APIs (optional) or an external command wrapper.
   - The key is: whichever LLM is used, it writes back into the same canonical `research/` workspace.

In both cases, the research state layer stays stable and tool-agnostic.

### 4.0.3 The three “full stacks” we could run (and why we pick one)

**Stack 1 (Recommended): Repo-local workspace + derived SQLite (today + v3)**

- Canonical: `research/` (Markdown/YAML + optional `activity.jsonl`)
- Retrieval: `index/erdos.sqlite` (FTS5 + embeddings optional)
- Orchestration: `erdos` CLI commands (+ MCP server as an interface for external agents)
- LLM: external command (existing) and/or direct APIs (optional later)

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

```
research/
  problems/
    0006/
      README.md
      SCRATCHPAD.md
      SYNTHESIS.md
      leads.yaml
      attempts.yaml
      sessions.yaml
      activity.jsonl          # append-only (optional but recommended)
  global/
    TECHNIQUES.md
    GLOSSARY.md
```

**Rules:**

- Markdown files are for free-form, human-readable thinking.
- YAML files are for structured items we must query/update deterministically.
- `activity.jsonl` is append-only operational trace (what changed, by whom, when).
- The existing “big text” stays gitignored:
  - literature extracts in `literature/extracts/`
  - loop logs in `logs/loop/`
  - search index in `index/`

### 4.2 Navigation UX (how humans + agents will use it)

Primary entrypoints:

- `erdos research init 6` → creates the folder + templates for Problem 6
- `erdos research open 6` → prints the path (and optionally opens in editor)
- `erdos research note 6 "..."` → appends to `SCRATCHPAD.md` (+ activity event)
- `erdos research lead add 6 --title ... --source ... --priority high` → writes `leads.yaml`
- `erdos research attempt log 6 --lean-file ... --result failed --run-log logs/loop/...` → writes `attempts.yaml`
- `erdos research status 6` → prints:
  - active session
  - top leads
  - last attempts + outcomes
  - next suggested actions
- `erdos research synthesize 6` → updates `SYNTHESIS.md` from:
  - scratchpad + leads + attempts + (optional) top retrieved sources

### 4.3 RAG integration (so notes actually help)

Add indexing of research artifacts into `index/erdos.sqlite` as additional chunks.

Minimal behavior:

- `erdos index --research 6` (or extend existing index build) reads:
  - `research/problems/0006/SYNTHESIS.md`
  - `research/problems/0006/SCRATCHPAD.md` (maybe last N chars)
  - possibly a rendered lead list (“Lead: … / status: …”)
- writes them as `chunks` with `problem_id=6` and a new `source_type` (e.g., `research_synthesis`, `research_scratchpad`)

Then:

- `erdos ask` automatically pulls these chunks as part of retrieval
- `erdos loop` can optionally include top research chunks in its prompt context

### 4.4 Loop integration (closing the iteration loop)

When `erdos loop` runs:

- it already emits detailed logs under `logs/loop/`
- v3 should also emit a single structured “attempt record” into:
  - `research/problems/{id}/attempts.yaml` (and an activity event)

This converts raw logs into *navigable state*.

---

## 5) Data contracts (explicit, so nothing is underspecified)

### 5.1 `leads.yaml` (structured, queryable)

```yaml
schema_version: 1
problem_id: 6
leads:
  - id: lead_20260123_001
    title: "Green–Tao theorem"
    status: new            # new | investigating | promising | dead_end | incorporated
    priority: high         # low | medium | high
    source:
      doi: "10.4007/annals.2008.167.481"
      arxiv_id: "math/0404188"
      url: null
    notes: "Seems directly relevant; figure out mapping to problem statement."
    created_at: "2026-01-23T00:00:00Z"
    updated_at: "2026-01-23T00:00:00Z"
```

### 5.2 `attempts.yaml` (attempt history)

```yaml
schema_version: 1
problem_id: 6
attempts:
  - id: att_20260123_001
    session_id: sess_20260123_001
    lean_file: "formal/lean/Erdos/Problem006.lean"
    run_log: "logs/loop/run_20260123_010203_ab12cd.jsonl"
    result: failed         # failed | partial | success
    summary: "Stuck on lemma X; need stronger induction hypothesis."
    created_at: "2026-01-23T00:00:00Z"
```

### 5.3 `sessions.yaml` (campaign/session tracking)

```yaml
schema_version: 1
problem_id: 6
active_session_id: sess_20260123_001
sessions:
  - id: sess_20260123_001
    goal: "Collect known results + identify Lean imports/lemmas."
    started_at: "2026-01-23T00:00:00Z"
    ended_at: null
    tags: ["survey", "lean_setup"]
```

### 5.4 `activity.jsonl` (append-only operational trace)

Each line is a JSON object (append-only):

```json
{"ts":"2026-01-23T00:00:00Z","actor":"human","event":"note_added","problem_id":6,"session_id":"sess_20260123_001","data":{"len":123}}
{"ts":"2026-01-23T00:05:00Z","actor":"erdos","event":"lead_added","problem_id":6,"session_id":"sess_20260123_001","data":{"lead_id":"lead_20260123_001"}}
```

---

## 6) Implementation slices (what to build first)

### Slice 1 — Workspace + templates + minimal CLI

- create `erdos research init/open/note/status`
- define the file layout + template creation
- keep it purely file-based (no DB)

### Slice 2 — Structured lead/attempt CRUD

- implement `lead add/list/update`
- implement `attempt log/list`
- guarantee stable IDs and schema_version checks

### Slice 3 — Index the workspace into the existing search DB

- extend indexing so `erdos ask` can retrieve research notes + synthesis
- (optional) include literature extracts as chunks if available

### Slice 4 — Loop integration and synthesis

- after `erdos loop`, automatically append an attempt record
- `erdos research synthesize` updates `SYNTHESIS.md` deterministically

---

## 7) Proposed Specs (post-review)

Next spec ID is **SPEC-023**. Suggested breakdown:

- **SPEC-023: Research Workspace (Filesystem Canonical)**
  - folder layout, templates, YAML schemas, CLI init/open/status/note
- **SPEC-024: Leads + Attempts (Structured Tracking)**
  - CRUD, validation, stable IDs, activity log
- **SPEC-025: Index Research Artifacts into Search DB**
  - new chunk sources, indexing rules, ask/loop retrieval integration
- **SPEC-026: Research Synthesis**
  - deterministic synthesis format, optional LLM assist, update rules

---

## 8) Senior-review questions (things to decide explicitly)

1) Should `research/` be git-tracked by default, or treated like `literature/cache/` (local-only)?
2) Do we want `activity.jsonl` as a required SSOT, or an optional operational trace?
3) How much should `erdos loop` automatically write into research state vs leaving it manual?
4) Should we index *all* scratchpad text or only curated synthesis (+ last N bytes of scratchpad)?
5) Do we need cross-problem linking (knowledge graph), or defer until v4?

---

## 9) References (web, 2025–2026)

- LangGraph persistence (Python): https://langchain-ai.github.io/langgraph/how-tos/persistence/
- LangGraph persistence (JS): https://langchain-ai.github.io/langgraphjs/how-tos/persistence/
- OpenAI Agents SDK sessions (Python): https://openai.github.io/openai-agents-python/sessions/
- OpenAI Agents SDK sessions (JS): https://openai.github.io/openai-agents-js/guides/sessions/
- Anthropic memory tool: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/memory-tool
- Letta memory blocks: https://docs.letta.com/concepts/memory-blocks
- mem0 overview: https://docs.mem0.ai/overview
- Zep docs: https://docs.getzep.com/
- Microsoft Agent Framework overview: https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/agent-framework/overview
- AutoGen memory: https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/memory.html
- Semantic Kernel agent memory: https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-memory?pivots=programming-language-python
- LlamaIndex Workflows state: https://docs.llamaindex.ai/en/stable/module_guides/workflow/state/
- Temporal docs: https://docs.temporal.io/
- Temporal Python dev guide: https://docs.temporal.io/dev-guide/python
- sqlite-vec: https://github.com/asg017/sqlite-vec
- sqlite-vss: https://github.com/asg017/sqlite-vss
- pgvector: https://github.com/pgvector/pgvector
