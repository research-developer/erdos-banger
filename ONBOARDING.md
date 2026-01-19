# Erdős-Banger: Contributor Onboarding

**TL;DR:** A CLI toolkit for researching and iteratively formalizing Erdős problems with LLM + Lean 4.

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

**Why this works:** Lean is the oracle. LLM can hallucinate all day, but Lean proofs either compile or they don't.

**Where we are today:** In v1.1, you can run this loop manually with `erdos ask` + `erdos lean check`. In v1.2, `erdos loop` automates the iteration.

---

## What This Is

- **CLI toolkit** for Erdős problem research (`erdos list`, `erdos search`, `erdos ingest`, `erdos ask`, `erdos lean …`)
- **Problem dataset harness**:
  - upstream: [teorth/erdosproblems](https://github.com/teorth/erdosproblems) (metadata-only YAML; included as a submodule)
  - v1 runtime input: a local **enriched** dataset at `data/problems_enriched.yaml` (titles/statements/references)
- **Literature pipeline** - ingests *known* references (DOI/arXiv) from problem metadata via Crossref + arXiv, and caches what’s legal
- **Search + Q&A** - SQLite FTS5 index + `erdos ask` prompt builder for citation-grounded answers (LLM is an external subprocess)
- **Lean 4 integration** - generate skeleton files, compile, capture errors, iterate

---

## What This Is NOT

- **Not an autonomous solver** - it's infrastructure to *assist* proving, not magic
- **Not a paper discovery engine** - v1 ingests references already listed on a problem; it does not find “recent papers” automatically
- **Not a web app** - CLI-first, designed for automation and AI agents
- **Not storing paywalled PDFs** - only metadata + open-access content (arXiv source); PDF conversion is deferred
- **Not promising breakthroughs** - we're building tools, not claiming victories
- **Not fully automated (yet)** - human guides the loop, LLM proposes, Lean verifies

---

## Why We Might Have a Chance

```
  PURE MATH PERSON                       US
       │                                  │
       ▼                                  ▼
  "I have an idea"                  "erdos ask 6 'what approaches exist?'"
       │                                  │
       ▼                                  ▼
  *thinks for 3 months*             *gets literature context in 30 seconds*
       │                                  │
       ▼                                  ▼
  "Let me try X"                    "erdos lean formalize 6"
       │                                  │
       ▼                                  ▼
  *writes informal proof*           *Lean checks each step*
       │                                  │
       ▼                                  ▼
  "I think it works?"               "COMPILES = VERIFIED"
       │                                  │
       ▼                                  ▼
  *submits to journal*              *submits with formal proof*
  *3 year review process*           *verification took 1 minute*
```

**Our edge:**
1. **Integrated tooling** that doesn't exist publicly
2. **Literature context** that pure Lean users don't have
3. **Formal verification** that informal math people skip
4. **Memory/logging** that ad-hoc ChatGPT users don't keep
5. **Systematic approach** vs. vibes-based shotgunning

You're not recreating something that exists. You're filling a real gap.

---

## The Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Upstream dataset            Metadata APIs            Literature           │
│   ┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐      │
│   │ erdosproblems   │      │ Crossref (DOI)  │     │ arXiv (source)  │      │
│   │ (metadata-only) │      │                 │     │                 │      │
│   └────────┬────────┘      └────────┬────────┘     └────────┬────────┘      │
│            │                        │                       │               │
└────────────┼────────────────────────┼───────────────────────┼───────────────┘
             │                        │                       │
             ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐      │
│   │ Problems YAML   │      │ Search Index    │     │ Literature      │      │
│   │ (gitignored)    │      │ (SQLite FTS5)   │     │ Cache           │      │
│   │                 │      │                 │     │                 │      │
│   │ • id, status    │      │ • text chunks   │     │ • manifests/    │      │
│   │ • title/stmt    │      │ • BM25 search   │     │ • cache/        │      │
│   │ • refs + tags   │      │                 │     │ • extracts/     │      │
│   └────────┬────────┘      └────────┬────────┘     └────────┬────────┘      │
│            │                        │                       │               │
└────────────┼────────────────────────┼───────────────────────┼───────────────┘
             │                        │                       │
             └────────────────────────┼───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI COMMANDS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│      Browse            Ingest        Search/Q&A        Formalize            │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│   │ list      │    │ ingest    │    │ search    │    │ lean init │          │
│   │ show      │    │           │    │ ask       │    │ lean check│          │
│   │ refs      │    │           │    │           │    │ formalize │          │
│   └───────────┘    └───────────┘    └───────────┘    │ loop      │          │
│                                                      └─────┬─────┘          │
│                                                            │                │
└────────────────────────────────────────────────────────────┼────────────────┘
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LEAN 4 PROJECT                                 │
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

Notes:
- `data/erdosproblems/` is upstream **metadata-only**; v1 requires a local enriched `data/problems_enriched.yaml` (see quickstart below).
- `erdos loop` is planned for v1.2; in v1.1 you run the loop manually.
- OpenAlex/Unpaywall integration is planned; v1.1 uses Crossref + arXiv.

---

## How We Work (Memory + Human Steering)

For most problems, brute-force “try random tactics until it compiles” doesn’t work — the search space is huge. The practical approach is:

- **Iterate**: propose a step → run `erdos lean check` → feed back errors → revise.
- **Record attempts**: write down what you tried, what failed, and the next promising idea, so you don’t repeat dead ends.
- **Prefer small steps**: one lemma / one patch at a time; keep diffs reviewable.
- **Use reproducible artifacts**: prompts, Lean errors, and patches should be saved so others (or future-you) can resume.

This philosophy is the motivation behind planned structured run logs (Spec-013): a local-first “attempt history” that a future web UI could display without requiring a server.

---

## First 15 Minutes

```bash
# 1. Clone and setup
git clone https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git
cd erdos-banger
git submodule update --init --recursive

# 2. Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# 3. Bootstrap sample data (for local development)
cp tests/fixtures/sample_problems.yaml data/problems_enriched.yaml

# 4. Verify CLI works
uv run erdos --version
uv run erdos list --limit 5

# 5. Look at a problem
uv run erdos show 6

# 6. See its references
uv run erdos refs 6

# 7. Search (build index for best results)
uv run erdos search "prime numbers" --build-index

# 8. Ask a question (prompt-only mode)
uv run erdos ask 6 "What partial results are known?" --no-llm

# 9. (Optional) Install Lean via elan
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
```

---

## Current Status (v1.1)

| Component | Status | Notes |
|-----------|--------|-------|
| CLI scaffold | ✅ Done | `list`, `show`, `refs`, `search`, `ingest`, `ask`, `lean …` |
| Problem loader | ✅ Done | Loads local enriched dataset (`data/problems_enriched.yaml`) |
| Ingest (arXiv/Crossref) | ✅ Done | Fetches metadata + caches arXiv source/extracts |
| Search (FTS5) | ✅ Done | BM25 full-text search |
| Ask (RAG Q&A) | ✅ Done | Builds citation-grounded prompt; optional LLM subprocess |
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
- **Problem 6** ($100, proved) — example of a proved problem with a prize
- **Problem 4** ($10,000, proved) — example of a higher-prize proved problem
- **Problem 148** (open; tagged “unit fractions”) — example of an open problem area

Some are solved. Some are open. Some have Lean formalizations. We're building tools to work on all of them.

---

## Philosophy

From [Google DeepMind's "Scaling Agent Systems"](https://arxiv.org/html/2512.08296v1):

> Start simple. Add agents only when necessary.

We're not building a complex multi-agent system yet. We're building **solid CLI infrastructure** that:
1. Works reliably
2. Has good test coverage
3. Produces reproducible results
4. Can support agents later (via MCP)

The fancy stuff comes after the plumbing works.

---

## Questions?

- **Full architecture:** `docs/specs/master-vision.md`
- **All specs:** `docs/specs/README.md`
- **Bugs/debt tracking:** `docs/bugs/README.md`, `docs/debt/README.md`

Or just ask in the repo issues.

---

*"The obstacle is the way."* — Marcus Aurelius (and also our GitHub org name)
