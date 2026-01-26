---
name: erdos
description: Complete guide to the Erdos CLI toolkit for mathematical research. Use when discussing Erdos problems, Lean formalization, literature search, or when the user asks about CLI commands, API costs, or environment configuration.
metadata:
  short-description: Erdos CLI reference & cost guide
---

# Erdos CLI Toolkit Reference

This skill provides comprehensive knowledge of the `erdos` CLI for collaborative research on Erdos problems.

## Quick Start

```bash
# See all commands
uv run erdos --help

# List open problems
uv run erdos list --status open --limit 10

# Show problem details
uv run erdos show 6

# Search problems
uv run erdos search "prime arithmetic"
```

## Cost Awareness

### $0 Commands (no paid APIs; some use free/rate-limited network)

| Command | Notes |
|---------|------|
| `erdos list`, `erdos show`, `erdos search` | Local dataset/index (semantic search uses local `sentence-transformers`) |
| `erdos refs problem`, `erdos logs`, `erdos dashboard` | Local files (`literature/`, `logs/`, workspace YAML) |
| `erdos ingest` | Free/rate-limited metadata APIs (OpenAlex/arXiv/Crossref); optional PDF conversion |
| `erdos refs s2`, `erdos refs zbmath` | Free/rate-limited APIs (Semantic Scholar, zbMATH) |
| `erdos sync ...` | Network sync/scrape; no paid API |
| `erdos lean init/check/status/formalize/import` | Lean tooling; downloads toolchain/mathlib as needed |

### Potentially billable commands (depends on your configuration)

| Command | When it can cost money |
|---------|-------------------------|
| `erdos ask` | Uses an external LLM unless `--no-llm` (via `ERDOS_LLM_COMMAND`) |
| `erdos loop run` | Uses an external LLM (via `ERDOS_LLM_COMMAND` / `--llm-cmd`) |
| `erdos convert --use-llm` / `erdos ingest --use-llm` | Marker LLM-enhanced extraction (Gemini/Claude/OpenAI, etc.) |
| `erdos lean prove` | Aristotle API (`ARISTOTLE_API_KEY`) |
| `erdos research exa search` | Exa Research API (`EXA_API_KEY`) |

## The Subscription Workaround

**Key insight:** You can bypass API costs by using Claude Code or Codex CLI directly.

Instead of running `erdos loop run` (which calls LLM APIs), you can:

1. **Generate skeleton (FREE):** `erdos lean formalize 6`
2. **Work with Codex (SUBSCRIPTION):** Ask me to help write/edit the proof
3. **Check compilation (FREE):** `erdos lean check formal/lean/Erdos/Problem006.lean`
4. **Iterate with me (SUBSCRIPTION):** Show errors, I fix them

This workflow uses your Claude/Codex subscription instead of per-token API calls.

## Command Reference

**SSOT:** `docs/developer/cli-reference.md` (auto-generated from the CLI). If any example below drifts, trust the CLI reference.

### Problem Discovery

```bash
# List with filters
erdos list --status open --prize-min 100 --limit 20
erdos list --tag "number theory" --status proved

# Show details
erdos show 6

# Search (FTS5 - free)
erdos search "prime arithmetic progressions"
erdos search "chromatic number" --limit 50

# Search (semantic/hybrid - local embeddings; downloads model weights on first run)
erdos search "density of primes" --semantic
erdos search "graph coloring" --hybrid --alpha 0.7
```

### Literature & References

```bash
# Local references
erdos refs problem 6

# Semantic Scholar (API, rate-limited)
erdos refs s2 citations 10.1234/example --limit 20
erdos refs s2 cited-by 10.1234/example
erdos refs s2 references 10.1234/example

# zbMATH (free API)
erdos refs zbmath --msc 11B05 --year-min 2020 --limit 50
```

### Ingestion (Fetching Literature)

```bash
# Single problem
erdos ingest 6 --source openalex

# Batch mode
erdos ingest --all --status open --limit 100 --dry-run
erdos ingest --all --status open --limit 100  # Execute

# With PDF conversion
erdos ingest 6 --pdf --pdf-converter marker
```

### Lean Formalization

```bash
# Initialize project (one-time)
erdos lean init

# Generate skeleton
erdos lean formalize 6  # Creates formal/lean/Erdos/Problem006.lean

# Import upstream formalization (if available)
erdos lean import 6

# Check compilation
erdos lean check formal/lean/Erdos/Problem006.lean

# Check status
erdos lean status 6

# Automated proving (PAID - uses Aristotle API)
erdos lean prove input.lean --output output.lean

# Copilot server (requires: uv sync --extra copilot)
erdos lean copilot serve --port 8080
```

### RAG Q&A

```bash
# Ask about a problem (PAID - uses LLM)
erdos ask 6 "What techniques have been used to approach this problem?"

# Retrieval only (FREE)
erdos ask 6 "relevant literature" --no-llm
```

### Proof Loop (Automated Iteration)

```bash
# Run iterative proof loop (PAID - heavy LLM usage)
erdos loop run 6 --max-iter 10

# Preview without writing
erdos loop run 6 --no-apply
```

### Research Workspace

```bash
# Initialize workspace
erdos research init 6

# Workspace convenience
erdos research open 6
erdos research note 6 "Tried density increment argument; stuck on lemma X"
erdos research status 6
erdos research synthesize 6

# Keep records tidy / validated
erdos research fmt 6
erdos research validate 6

# Manage leads
erdos research lead add 6 --title "Green-Tao approach" --doi 10.1234/example
erdos research lead list 6
erdos research lead update 6 <lead-id> --status promising --priority high

# Track hypotheses
erdos research hypothesis add 6 --statement "Density argument works" --confidence high
erdos research hypothesis list 6 --status active
erdos research hypothesis update 6 <hyp-id> --status refuted

# Track tasks + attempts
erdos research task add 6 --title "Read paper X" --status todo --priority medium
erdos research task list 6 --status todo
erdos research task update 6 <task-id> --status doing --priority high
erdos research attempt log 6 --result failed --summary "Could not close gap in step 3" --kind manual
erdos research attempt list 6 --result failed

# Exa search (PAID)
erdos research exa search 6 "prime gaps density arguments" --max-results 10 --save-leads
```

### Data Sync

```bash
# Update submodule (FREE)
erdos sync submodule

# Fetch from website (scraping)
erdos sync website 6

# Extract proof links / sync Lean statements
erdos sync proof 6 --dry-run
erdos sync statements 6 --dry-run

erdos sync all --problems 6 --skip-proof
```

## Environment Configuration

**SSOT:** `.env.example` (and `docs/developer/configuration.md` for deeper details).

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

### LLM Configuration (Cost Drivers)

```bash
# Default LLM command (used by erdos ask/loop)
ERDOS_LLM_COMMAND=./scripts/llm.sh

# Per-task routing (optional)
ERDOS_LLM_COMMAND_MATH=./scripts/llm.sh    # For erdos ask
ERDOS_LLM_COMMAND_CODE=./scripts/llm.sh    # For erdos loop

# OpenAI (most common)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5.2-pro
OPENAI_REASONING_EFFORT=xhigh

# Anthropic (alternative)
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-opus-4-5-20251101
```

### Academic APIs (Mostly Free/Rate-Limited)

```bash
# Email for polite pools (faster rate limits)
ERDOS_MAILTO=your-email@example.com

# OpenAlex (optional key for higher limits)
OPENALEX_API_KEY=your-key-here

# Semantic Scholar (optional, 100 req/5 min without key)
SEMANTIC_SCHOLAR_API_KEY=your-key-here

# Exa Research (required for erdos research exa)
EXA_API_KEY=your-key-here
```

### Lean Proving

```bash
# Aristotle API (for erdos lean prove)
ARISTOTLE_API_KEY=arstl-your-key-here
```

## Working with Codex CLI Directly

When you want to use your subscription instead of API calls, **I can read AND edit any file in this repo directly.**

### What I Can Edit (Your Subscription = $0 API Cost)

| File Type | Location | What I Can Do |
|-----------|----------|---------------|
| **Lean proofs** | `formal/lean/Erdos/*.lean` | Write tactics, fix errors, add lemmas |
| **Problem data** | `data/problems_enriched.yaml` | Add/edit problem metadata, refs, tags |
| **Literature manifests** | `literature/manifests/*.yaml` | Add references, update metadata |
| **Research notes** | `literature/cache/*.md` | Analyze papers, write summaries |
| **Config files** | `.env`, `pyproject.toml` | Adjust settings, add API keys |
| **Source code** | `src/erdos/**/*.py` | Fix bugs, add features |
| **Tests** | `tests/**/*.py` | Write test cases |

### For Proving Problems

1. **Ask me to read the problem:** "Read Problem 6 and explain the mathematical statement"
2. **Generate skeleton:** `uv run erdos lean formalize 6`
3. **Ask me to work on the Lean file:** "Edit formal/lean/Erdos/Problem006.lean and fill in the proof"
4. **I'll edit the file directly** - no copy/paste needed
5. **Check compilation:** `uv run erdos lean check formal/lean/Erdos/Problem006.lean`
6. **Iterate with me** - show me errors, I'll edit the file again

### For Research

1. **Ask me to search:** "What references do we have for Problem 6?"
2. **I'll read files directly** from `literature/manifests/` and `data/`
3. **Ask me to analyze papers:** I can read PDFs and markdown in `literature/cache/`
4. **Ask me to add references:** "Add this paper to the manifest for Problem 6"

### For Data Management

1. **Edit problem metadata:** "Update Problem 6's status to 'partially_solved'"
2. **Add tags:** "Add the 'number-theory' tag to Problem 6"
3. **Manage references:** "Add this DOI to Problem 6's references"
4. **Rebuild index:** `uv run erdos search --build-index`

### For Understanding the Codebase

1. **Ask about architecture:** I can read `docs/index.md` and explore `src/erdos/`
2. **Ask about specific commands:** I can read the command implementations
3. **Ask about data:** I can query the local YAML files and SQLite index

## File Locations (All Readable & Editable)

| Path | Contents | Editable? |
|------|----------|-----------|
| `formal/lean/Erdos/*.lean` | Lean proof files | **YES** - I write proofs here |
| `data/problems_enriched.yaml` | Problem data (titles, statements, refs) | **YES** - I can update metadata |
| `data/erdosproblems/` | Upstream submodule | NO - sync only, don't edit |
| `literature/manifests/*.yaml` | Reference metadata per problem | **YES** - I can add refs |
| `literature/cache/` | Downloaded arXiv sources, PDFs | **YES** - I can add notes |
| `index/erdos.sqlite` | SQLite FTS5 search index | NO - rebuilt by CLI |
| `logs/runs.jsonl` | Execution history | NO - append-only log |
| `.env` | API keys and config | **YES** - I can help configure |

## Global Options

All commands support:

```bash
--json          # Machine-readable JSON output
--log-level     # DEBUG, INFO, WARN, ERROR
--version       # Show version
--help          # Command help
```
