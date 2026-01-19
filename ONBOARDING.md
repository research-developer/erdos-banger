# Erdős-Banger: Contributor Onboarding

**TL;DR:** A CLI toolkit for iteratively proving Erdős problems with LLM + Lean 4.

---

## What Are We Building?

A **human-in-the-loop proving workbench** that combines:
- **LLM** (hypothesis generator) - proposes Lean proof code
- **Lean 4** (ground truth verifier) - accepts or rejects with errors
- **Human** (pilot) - guides strategy, picks problems, steers iterations

```
┌─────────────────────────────────────────────────────────────────┐
│                        THE CORE LOOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    ┌─────────┐                                                  │
│    │  Human  │ ←───── picks problem, guides strategy            │
│    └────┬────┘                                                  │
│         │                                                       │
│         ▼                                                       │
│    ┌─────────┐      "try proving via induction"                 │
│    │   LLM   │ ←───── proposes Lean code                        │
│    └────┬────┘                                                  │
│         │                                                       │
│         ▼                                                       │
│    ┌─────────┐                                                  │
│    │  Lean 4 │ ←───── compiles: PASS or FAIL + errors           │
│    └────┬────┘                                                  │
│         │                                                       │
│         ▼                                                       │
│    ┌──────────────────┐                                         │
│    │  Success?        │                                         │
│    └────┬────────┬────┘                                         │
│         │        │                                              │
│        YES      NO                                              │
│         │        │                                              │
│         ▼        ▼                                              │
│      [DONE]   [Errors fed back to LLM]                          │
│                  │                                              │
│                  └──────► Human: "try different tactic"         │
│                                    │                            │
│                                    └────── loop back ───────►   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why this works:** Lean is the oracle. LLM can hallucinate all day, but Lean proofs either compile or they don't. No fake math possible.

---

## What This Is

- **CLI toolkit** for Erdős problem research (`erdos list`, `erdos search`, `erdos lean check`, etc.)
- **Data harness** using [Terence Tao's erdosproblems dataset](https://github.com/teorth/erdosproblems) (1135 problems)
- **Literature pipeline** - fetches paper metadata from arXiv/Crossref, caches source files
- **RAG Q&A** - search indexed content, ask questions with citations
- **Lean 4 integration** - create skeletons, compile, capture errors, iterate
- **Logging** - every run is logged for reproducibility

---

## What This Is NOT

- **Not an autonomous solver** - it's infrastructure to *assist* proving, not magic
- **Not a web app** - CLI-first, designed for automation and AI agents
- **Not storing paywalled PDFs** - only open-access content and metadata
- **Not promising breakthroughs** - we're building tools, not claiming victories
- **Not fully automated (yet)** - human guides the loop, LLM proposes, Lean verifies

---

## The Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   teorth/erdosproblems          Metadata APIs           Literature          │
│   ┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐      │
│   │ 1135 problems   │      │ Crossref (DOI)  │     │ arXiv (source)  │      │
│   │ (YAML dataset)  │      │ OpenAlex (meta) │     │ Unpaywall (OA)  │      │
│   └────────┬────────┘      └────────┬────────┘     └────────┬────────┘      │
│            │                        │                       │               │
└────────────┼────────────────────────┼───────────────────────┼───────────────┘
             │                        │                       │
             ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐      │
│   │ Problem DB      │      │ Search Index    │     │ Literature      │      │
│   │ (SQLite)        │      │ (SQLite FTS5)   │     │ Cache           │      │
│   │                 │      │                 │     │                 │      │
│   │ • id, status    │      │ • text chunks   │     │ • manifests/    │      │
│   │ • statement     │      │ • BM25 search   │     │ • cache/        │      │
│   │ • references    │      │                 │     │ • extracts/     │      │
│   └────────┬────────┘      └────────┬────────┘     └────────┬────────┘      │
│            │                        │                       │               │
└────────────┼────────────────────────┼───────────────────────┼───────────────┘
             │                        │                       │
             └────────────────────────┼───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI COMMANDS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Browse            Ingest            Search/Q&A         Formalize          │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐         │
│   │ list      │    │ ingest    │    │ search    │    │ lean init │         │
│   │ show      │    │           │    │ ask       │    │ lean check│         │
│   │ refs      │    │           │    │           │    │ lean form │         │
│   └───────────┘    └───────────┘    └───────────┘    │ loop      │         │
│                                                      └─────┬─────┘         │
│                                                            │               │
└────────────────────────────────────────────────────────────┼───────────────┘
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LEAN 4 PROJECT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   formal/lean/                                                              │
│   ├── Erdos/Problem006.lean    ◄── generated skeleton with `sorry`          │
│   └── ...                                                                   │
│                                                                             │
│                         lake build                                          │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  PASS or FAIL   │ ◄── errors fed back to loop          │
│                    └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## First 15 Minutes

```bash
# 1. Clone and setup
git clone https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git
cd erdos-banger
git submodule update --init

# 2. Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# 3. Verify CLI works
uv run erdos --version
uv run erdos list --limit 5

# 4. Look at a problem
uv run erdos show 6

# 5. See its references
uv run erdos refs 6

# 6. Search the index
uv run erdos search "prime numbers"

# 7. (Optional) Install Lean via elan
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
```

---

## Current Status (v1.1)

| Component | Status | Notes |
|-----------|--------|-------|
| CLI scaffold | ✅ Done | `list`, `show`, `refs`, `search`, `lean` |
| Problem loader | ✅ Done | 1135 problems from upstream dataset |
| Ingest (arXiv/Crossref) | ✅ Done | Metadata + source caching |
| Search (FTS5) | ✅ Done | BM25 full-text search |
| Ask (RAG Q&A) | ✅ Done | Citation-grounded answers |
| Lean check | ✅ Done | Compile + error parsing |
| Lean formalize | ✅ Done | Skeleton generation |
| Loop command | 🚧 v1.2 | Iterative LLM+Lean loop |
| Vector search | 📋 v1.3 | Semantic embeddings |
| MCP server | 📋 v1.4 | AI tool integration |

---

## Key Insight: Why Lean?

**LLMs hallucinate. Lean doesn't.**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   LLM: "Here's a proof that P = NP"                         │
│                                                             │
│   Lean: "Error on line 47: type mismatch, expected          │
│          `Decidable (P = NP)`, got `sorry`"                 │
│                                                             │
│   Reality: ❌ Proof rejected. Math is safe.                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Lean is a **formal proof assistant**. A proof either compiles or it doesn't. This makes it the perfect "ground truth oracle" for an LLM-assisted workflow:

- LLM proposes (creative, fast, possibly wrong)
- Lean verifies (rigorous, slow, always correct)
- Human guides (strategic, picks battles)

---

## The Erdős Problems

[Paul Erdős](https://en.wikipedia.org/wiki/Paul_Erd%C5%91s) was a legendary mathematician who posed thousands of problems, many with cash prizes. [Terence Tao's dataset](https://github.com/teorth/erdosproblems) catalogs 1135 of them.

Examples:
- **Problem 6** ($100, proved): Small primes in arithmetic progressions
- **Problem 4** ($10,000, proved): Arithmetic progressions in primes
- **Problem 148** (open): Unit fractions representation

Some are solved. Some are open. Some have Lean formalizations. We're building tools to work on all of them.

---

## Philosophy

From [Google DeepMind's "Scaling Agent Systems"](https://arxiv.org/html/2512.08296v1):

> Start simple. Add agents only when necessary.

We're not building a complex multi-agent system yet. We're building **solid CLI infrastructure** that:
1. Works reliably
2. Has good test coverage
3. Produces reproducible results
4. Can support agents later (via MCP, skills)

The fancy stuff comes after the plumbing works.

---

## Questions?

- **Full architecture:** `docs/specs/master-vision.md`
- **All specs:** `docs/specs/README.md`
- **Bugs/debt tracking:** `docs/bugs/README.md`, `docs/debt/README.md`

Or just ask in the repo issues.

---

*"The obstacle is the way."* — Marcus Aurelius (and also our GitHub org name)
