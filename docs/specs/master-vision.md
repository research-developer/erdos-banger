# Erdős Problem Research Harness – Design & Build Plan

## 1) Recommended Repo Name + Positioning

### Name Candidates (no hype)

- `erdos-banger` (concise and descriptive)
- `problem-lab`
- `erdos-lab`
- `erdos-workbench`
- `prizeworkbench`
- `resolute-cli`
- `conjecture-cli`
- `ep-research-kit` (EP = Erdős Problems)
- `lean-erdos-kit`
- `open-erdos`

**Chosen Name:** `erdos-banger`

**Tagline:** CLI-first toolkit for collaborative research on Erdős problems, from literature to Lean formalization.

### What It Is

- A CLI toolkit for Erdős problem research (no GUI needed for v1).
- A data-driven harness using Terence Tao's erdosproblems dataset as the ground truth of problem statements and metadata.
- A retrieval and formalization pipeline combining literature search, hybrid search (text + vectors), and Lean 4 theorem proving.
- A reproducible environment for human researchers and AI agents to iterate on problems, with structured logs and stable outputs.
- A legal and open platform: uses openly licensed data (Apache-2.0 for erdosproblems, CC licenses for literature when available) and respects content rights.

### What It Is Not

- Not a general unsolved math solver or competitor to Clay Millennium Problem solvers – scope is strictly Erdős problems (1135 problems curated by the community).
- Not an AI agent claiming to solve problems automatically – it's infrastructure to assist researchers, not a promise of breakthroughs.
- Not a web app or GUI – v1 is CLI-first with a focus on automation and integration (though future UI or web dashboards could build on it).
- Not a closed proprietary system – it won't store paywalled papers or scraped PDFs in the repo; it relies on metadata and legal open-access content only.
- Not a one-off script collection – it aims for production-grade CLI quality (structured output, test coverage, config management, versioning) from the start.

---

## 2) Architecture Overview (One Page)

The harness is composed of modular components that work together in a pipeline. Key components and their roles:

### Problem Dataset Import

Leverages Terence Tao's `teorth/erdosproblems` repository as a git submodule or managed snapshot to load problem **metadata** (YAML format). This is the canonical source for status, prizes, tags, and formalization metadata (Apache-2.0 licensed). The upstream `data/problems.yaml` is **metadata-only** (no titles/statements; no reference lists). The harness uses a local enriched dataset (`data/problems_enriched.yaml`, Spec 005) to add titles/statements/references while treating upstream metadata as SSOT.

### Literature Ingestion & Manifests

Handles reference material for a given problem. For each problem or reference, the harness can fetch metadata (OpenAlex as primary, Crossref as fallback) and open-access content (via arXiv source tarballs) if legally available. Instead of storing PDFs, it records manifests: JSON or YAML listing each source with metadata, URL, and cache status. Full texts are only stored in a private cache if permitted (e.g. arXiv HTML or source) and are not checked into git.

**Deduplication Strategy:**

OpenAlex handles deduplication internally via fingerprinting algorithms that match:
- arXiv preprint ↔ published journal version
- Multiple DOIs for the same work
- Different repository copies

**We do NOT need our own deduplication logic** if we use OpenAlex correctly as the primary metadata source. OpenAlex already aggregates and deduplicates data from Crossref, arXiv, PubMed, MAG, and institutional repositories.

**Ingest Flow (v1.2+):**
```
erdos ingest <id>
    │
    ├─► For each reference:
    │   │
    │   ├─► Query OpenAlex (unified, deduped metadata)
    │   │   └─► If found: use OpenAlex record
    │   │   └─► If not found: fallback to Crossref (DOI) or skip
    │   │
    │   ├─► If arXiv source needed:
    │   │   └─► arXiv e-print API (content only, not metadata)
    │   │
    │   └─► Write manifest entry
    │
    └─► Return CLIOutput with manifest
```

### Storage Layer (Metadata + Cache)

Uses a local database (default SQLite for simplicity) to store structured metadata: problem records, reference metadata, chunked text, etc. (Future: vector embeddings for semantic/hybrid search.) For v1, SQLite with FTS5 provides a lightweight full-text index. A separate local folder (e.g. `literature/cache/`) holds cached content like arXiv source or HTML, and possibly pre-processed text, keyed by content hashes/IDs. Nothing that violates licenses will be stored in git; the cache is user-local and git-ignored (see Legal Policy).

### Hybrid Index (Search)

Combines lexical search (e.g. BM25 via SQLite FTS5) and (future) vector similarity for semantic search. **V1 uses SQLite FTS5 only**. Vector embeddings and vector stores (FAISS/pgvector/Qdrant) are deferred until the core BM25 pipeline is stable.

### Lean4 Workspace

A structured Lean 4 project (`formal/lean/`) managed by Lean's package manager Lake and version manager elan. This contains the formalization attempts: definitions, conjectures, partial proofs, etc. Lean 4 and mathlib4 are set up as dependencies. The harness can create Lean files (problem statements, known lemmas) and compile them. Lean's output (errors, warnings) is captured and fed back to guide the next iteration. The Lean toolchain (via elan) ensures consistent versions – elan will pick the version from a `lean-toolchain` file and download it if needed.

### CLI Commands

A unified `erdos` CLI with subcommands (`list`, `show`, `refs`, `ingest`, `search`, `ask`, `lean`, `loop`, etc. – defined in detail below). Each command is implemented with robust argument parsing, error handling, and optional JSON output for automation. We use **Typer + Rich** (Spec 004). The CLI is designed for both interactive use and as an API for agents (deterministic outputs, machine-readable JSON with `--json`, no interactive prompts unless `--yes`/`--no-input` flags are used).

### Logging & Eval Harness

Every run produces structured logs (e.g. JSON lines or YAML) capturing the operations performed, external calls (with timestamps, parameters), and results. For instance, a search command log would include the query and the list of retrieved sources with their IDs and similarity scores. A lean check log would include the Lean version, file hashed, compile success/failure, and error messages. These logs go to `logs/` (git-ignored) and can be used to evaluate progress over time. We also define some metrics: e.g. number of formal definitions added, Lean proofs completed, retrieval accuracy (perhaps measured later by human or known relevant references).

### Optional MCP Layer

(Pluggable, not required for v1) The Model Context Protocol (MCP) is an open standard for connecting AI assistants to tools. Our CLI can optionally be wrapped or complemented by an MCP server exposing certain functions (like `search_index`, `get_problem`, `run_lean`) to AI clients like Claude Desktop. This is not mandatory in v1 since our CLI plus Claude's local skills suffice, but we keep it in mind. The design allows an MCP integration without refactoring – e.g. by a lightweight wrapper that calls the same underlying Python functions that the CLI uses. If a user runs an MCP server, the model could directly call "tools" instead of shelling out, but in v1, shell command execution is assumed (the model can run `erdos ...` commands in a sandbox).

### Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   teorth/erdosproblems          External APIs              Literature       │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐     │
│   │ problems.yaml   │      │ Crossref        │      │ arXiv           │     │
│   │ (metadata SSOT) │      │ OpenAlex        │      │ Unpaywall       │     │
│   └────────┬────────┘      │ Semantic Scholar│      │ CORE            │     │
│            │               └────────┬────────┘      └────────┬────────┘     │
│            │                        │                        │              │
└────────────┼────────────────────────┼────────────────────────┼──────────────┘
             │                        │                        │
             v                        v                        v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐     │
│   │ Problem DB      │      │ Search Index    │      │ Literature      │     │
│   │ (SQLite)        │      │ (SQLite FTS5)   │      │ Cache           │     │
│   │                 │      │                 │      │                 │     │
│   │ • problems      │      │ • text chunks   │      │ • manifests/    │     │
│   │ • references    │      │                 │      │ • cache/        │     │
│   │ • metadata      │      │                 │      │ • extracts/     │     │
│   └────────┬────────┘      └────────┬────────┘      └────────┬────────┘     │
│            │                        │                        │              │
└────────────┼────────────────────────┼────────────────────────┼──────────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                                      v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI COMMANDS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Info Display        Ingestion           Search/Q&A         Formalization  │
│   ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐    │
│   │ list      │      │ ingest    │      │ search    │      │ lean init │    │
│   │ show      │      │ index     │      │ ask       │      │ lean check│    │
│   │ refs      │      │           │      │           │      │ lean form │    │
│   └───────────┘      └───────────┘      └───────────┘      │ loop      │    │
│                                                            └─────┬─────┘    │
│                                                                  │          │
└──────────────────────────────────────────────────────────────────┼──────────┘
                                                                   │
                                                                   v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LEAN 4 PROJECT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   formal/lean/                                                              │
│   ├── lean-toolchain        (version pin)                                   │
│   ├── lakefile.lean         (dependencies: mathlib4)                        │
│   └── Erdos/                                                                │
│       ├── Problem001.lean   (generated skeletons)                           │
│       └── ...                                                               │
│                                      │                                      │
│                                      v                                      │
│                               lake build                                    │
│                                      │                                      │
│                                      v                                      │
│                           errors / proofs                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOGGING & EVAL                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   logs/                                                                     │
│   ├── runs.jsonl            (structured run records)                        │
│   ├── batch_state.json      (batch operation state)                         │
│   └── ...                                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Note: In the diagram, "lean form" is shorthand for `erdos lean formalize`.

**Data Flow:**
1. **Import** → Problem dataset loads into SQLite, external APIs enrich references
2. **Index** → Text chunks populate the FTS5 search index (v1); embeddings are a future extension
3. **Query** → CLI commands read/write to storage, invoke Lean compilation
4. **Iterate** → Lean errors feed back to LLM loop, all steps logged

**Diagram Summary:** The dataset feeds the problem DB. Ingestion fetches references (via external APIs) into manifests and possibly cached text. An index builder uses the DB content (problem statements, reference texts) to create a lexical search index (FTS5) in v1; vector embeddings and hybrid reranking are a future extension. The CLI commands orchestrate these: e.g., `erdos search` queries the index and returns relevant text chunks with citations; `erdos ask` uses LLM (via CLI integration) to answer questions with those citations. The Lean project is initialized by `erdos lean init` and contains Lean files. Commands like `erdos lean formalize` create a Lean stub for a problem, and `erdos loop` runs an iterative loop where the LLM proposes proofs, Lean checks them, and feedback is logged. Logging happens throughout to enable reproducibility and evaluation.

---

## 3) Repo Structure

Below is the **current** repository layout (SSOT as of v1.1). Directories are marked with a trailing `/`. We indicate which parts are committed to git vs generated/ignored.

```text
erdos-banger/
├── src/erdos/                    # Python package (committed)
│   ├── cli.py                    # Typer entry point + global flags
│   ├── commands/                 # CLI subcommands (list/show/refs/search/ingest/ask/lean)
│   ├── core/                     # Core logic (loader, search index, ingest, ask, Lean runner)
│   ├── templates/                # Jinja2 templates (e.g., `lean_skeleton.j2`)
│   └── data/                     # Built-in sample dataset (`problems_enriched.yaml`)
├── tests/                        # pytest suite + fixtures (committed)
├── docs/                         # specs, bugs/debt, protocol, archive (committed)
│   ├── INDEX.md
│   ├── specs/
│   ├── bugs/
│   ├── debt/
│   ├── _archive/
│   └── _ralphwiggum/
├── data/                         # local + upstream datasets
│   └── erdosproblems/            # teorth/erdosproblems submodule (metadata-only; committed via git submodule)
├── data/problems_enriched.yaml   # local enriched dataset (gitignored; priority 2 - see note below)
├── literature/manifests/         # reference manifests (committed)
├── literature/cache/             # downloads (gitignored)
├── literature/extracts/          # extracted text (gitignored)
├── index/*.sqlite                # SQLite FTS index (gitignored)
├── formal/lean/                  # Lean project scaffold (committed)
├── formal/lean/.lake/            # Lean deps/build artifacts (gitignored)
├── logs/                         # run logs (gitignored)
├── scripts/                      # helper scripts (committed)
├── Makefile                      # local dev + CI convenience targets (committed)
├── pyproject.toml / uv.lock      # deps + tool configs (committed)
└── PROMPT.md / PROGRESS.md       # Ralph Wiggum loop prompt + state (committed)
```

### What's Committed vs Ignored

**Committed:**
- All code (CLI, core logic, model schemas, docs), config, and small metadata like manifests and Lean source files
- The erdosproblems dataset (as a submodule to keep it separate but versioned)
- Structured manifests (YAML/JSON listing reference metadata) – these contain DOIs, arXiv IDs, etc., but not full paper text
- Lean files and their updates (this is part of our work product)
- Ralph Wiggum protocol docs under `docs/_ralphwiggum/` and loop state files (`PROMPT.md`, `PROGRESS.md`) are committed so they can be shared and versioned

**Git-ignored:**
- Any large or non-redistributable data, including:
  - The literature fulltext cache (`literature/cache/`)
  - Any extracted full texts (`literature/extracts/`)
  - Search index files and databases (`index/` contents except config)
  - Lean build artifacts (`formal/lean/build/` and the downloaded mathlib library)
  - Run logs
- These are either generated or user-specific. We provide ways to regenerate from source metadata when possible. For example, a collaborator can run `erdos ingest 1` to fetch and parse references for problem 1 if they have network access, rather than storing those bulky files in git.

**Data submodule strategy:** Include `teorth/erdosproblems` via a git submodule pinned to a specific commit (reproducible metadata). Treat `data/erdosproblems/` as external upstream data.

**Dataset priority order (SSOT: `src/erdos/core/problem_loader.py`):** The CLI resolves `problems_enriched.yaml` in this order:

1. `ERDOS_DATA_PATH` environment variable (explicit override; file or directory)
2. `./data/problems_enriched.yaml` (user-provided, gitignored; priority for local development)
3. Built-in package data `src/erdos/data/problems_enriched.yaml` (committed sample dataset)
4. Upstream submodule `data/erdosproblems/data/problems.yaml` (metadata-only fallback)

For most users: create `data/problems_enriched.yaml` locally (gitignored); CI and packaged installs use the built-in sample.

### Schema & Model Files

We'll have Pydantic models in `src/erdos/core/models/` (SSOT: `docs/_archive/specs/spec-003-domain-models.md`) for key entities:

- **ProblemRecord:** Enriched internal representation used by the CLI. The upstream `teorth/erdosproblems` `data/problems.yaml` is metadata-only (no titles/statements); we supplement it via local enrichments and/or other sources (see Spec 005). Fields include `id`, `status`, `prize`, `tags`, plus enriched fields like `title`, `statement`, `references`, `notes`, and `formalized`.

- **ReferenceRecord:** A literature source, with fields like `key` (a short id, e.g. "Erdos1965" or a DOI), `title`, `authors`, `venue`, `year`, `doi`, `arxiv_id`, `url` (if available), `oa_status`, `license`, etc. This is populated via metadata services (Crossref for DOI-based references, arXiv API for preprints, etc.). It also includes a field `local_pdf_path` or similar if we have a cached copy, and flags like `legal_status` (e.g. "open-access", "author-postprint", or "unknown").

- **ManifestEntry:** (Maybe same as ReferenceRecord or wrapping it) – if needed, a per-problem manifest listing references. Could be a JSON file with structure: for each reference, store the metadata plus maybe a pointer to where the content can be found (like "in arXiv, ID=xyz", or "available via Unpaywall at URL", etc.), plus a hash of content if downloaded. The manifest version can be stored (for migrations if schema changes). This is what goes in `literature/manifests/`.

- **TextChunk:** When indexing, we will chunk documents (e.g. split a paper into sections or paragraphs). A chunk record might have `id`, `reference_id` (link to ReferenceRecord), `text` (the raw text snippet), and `embedding` (vector or a key to a vector store). These chunks are what the retrieval returns as context to answer questions.

- **LeanCheckResult:** Data structure for Lean compile results – e.g. `file` (Lean file name), `errors` (list of errors with position, message), `status` (pass/fail). This will be serialized to JSON when `erdos lean check` runs with `--json`.

We will maintain schema version fields in these JSON/YAML structures. For example, ManifestEntry might have `"schema_version": 1` so that if we improve our manifest format, we can handle older versions gracefully (the CLI could detect and migrate if needed).

All JSON output from commands will include a top-level `schema_version` and command info (so that parsers know how to interpret it). This helps maintain backward compatibility as the CLI evolves.

---

## 4) CLI Spec (V1)

The CLI, invoked as `erdos`, supports multiple subcommands corresponding to stages of the workflow. Each command follows consistent conventions:

- Non-interactive by default in v1.1 (no prompts).
- Returns exit code 0 on success, nonzero on failure (different codes for different failure types).
- Supports machine-readable output via the `CLIOutput` JSON envelope (`schema_version`, `command`, `success`, `data`, `error`, plus timing fields).
- Global flags implemented in v1.1 (SSOT: `src/erdos/cli.py`):
  - `--json` (machine-readable output)
  - `--log-level` (e.g. DEBUG/INFO/WARN/ERROR)
  - `--version` (print version and exit)

Command-specific flags vary by command (SSOT: `erdos <command> --help`). In v1.1, for example, `erdos ingest` supports `--no-network` and `--no-download`.

### Commands and Usage

#### 1. `erdos list [filters]`

List problems with optional filters. This reads the problem data (from the YAML or our imported JSON).

**Filters (v1.1 SSOT):**
- `--status` (e.g. `open`, `proved`, `disproved`, `partially_solved`, `unknown`)
- `--prize-min INT`, `--prize-max INT`
- `--tag TEXT` (repeatable)
- `--limit INT`

For instance, `erdos list --status open --prize-min 1000` lists open problems with prize ≥ $1000.

**Output (v1.1):**
- Human: a table with ID, status, prize, title, tags
- JSON: a `CLIOutput` envelope containing a list of problem summaries (SSOT: `erdos.core.models.CLIOutput`)

**Exit codes (v1.1):** Exit code 0 on success (including empty results). Nonzero only for errors (e.g., dataset parse failure).

**No network required.**

**Example:** `erdos list --status open --tag "graph theory"` might output a filtered list. If `--json`, it outputs JSON list of problems.

#### 2. `erdos show <problem_id>`

Show detailed info for a single problem.

**Input:** A problem ID or number (like `erdos show 42`).

**Behavior:** Loads that problem from the dataset. Outputs the full problem statement, status, prize info, tags, and references list. Essentially a nicely formatted view of the YAML entry.

**In JSON (v1.1):** Returns a `CLIOutput` envelope containing the full `ProblemRecord` under `data`. References are the problem's embedded `ReferenceEntry` records from the enriched dataset.

**No network.**

**Errors:** Nonzero exit if problem_id not found (exit code e.g. 3 for "not found").

**Example (v1.1):** `erdos show 6 --json` emits a `CLIOutput` envelope:
- `data.id`, `data.title`, `data.statement`, `data.status`, `data.prize`, `data.tags`
- `data.references[]` entries (key, citation, optional doi/arXiv/url)
- `timestamp`, `duration_ms` for observability

In human output, could show a markdown-like output (title, statement, references enumerated).

**Contract:** Stable fields in JSON so that external tools (or LLM agents) can parse problem details easily.

#### 3. `erdos refs <problem_id>`

List references for a problem, with available metadata.

**Behavior (v1.1):** Lists `ProblemRecord.references` from the enriched problems dataset. `erdos refs` is read-only and does not perform network calls.

**Output (v1.1):**
- Human: a table of embedded references (key, citation, optional DOI/arXiv).
- JSON: `CLIOutput` envelope with `data.problem_id` and `data.references[]`.

#### 4. `erdos ingest <problem_id>`

Ingest (fetch) reference data for a problem. This is a key step involving external APIs, and may be interactive or lengthy.

**v1.1 SSOT:** `docs/_archive/specs/spec-010-ingest-command.md`. In v1.1, ingest is intentionally scoped to:
- arXiv metadata + source tarball caching + best-effort plain-text extract
- Crossref metadata for DOI references (no full-text download)
- No Unpaywall/OpenAlex/Semantic Scholar fallbacks
- No PDF conversion (deferred; see Spec 019)

**Behavior:** Looks up each reference associated with the problem:
- If a reference has a DOI, use the Crossref API to fetch bibliographic metadata (metadata-only in v1.1).
- If it has an arXiv ID, use the arXiv export API to fetch metadata and (unless downloads are disabled) cache the arXiv source tarball and write a best-effort plain-text extract.
- If it has neither, skip it with a structured "no identifier" reason (do not attempt resolution/search in v1.1).

For each reference:
- Create a ReferenceRecord with metadata
- For arXiv references, cache the source tarball under `literature/cache/` and write extracts under `literature/extracts/` (both git-ignored).
- Save a manifest file `literature/manifests/<id>.yaml` with reference entries and checksums for reproducibility.

**Future extensions (explicitly not in v1.1):**
- OpenAlex as a primary metadata source (Spec 020, v1.2+)
- Open-access link discovery (e.g., Unpaywall) (future spec)
- PDF conversion for non-arXiv references via Marker `[pdf]` extra (Spec 019, v2.0+)

**Output:** In human mode, print a summary: e.g. "Fetched 3 references. 1 arXiv source cached + extract written, 2 metadata-only." JSON output would detail each reference and what happened.

**Idempotence:** Running `erdos ingest` again should skip already ingested references unless a `--force` is given to refresh.

**Network:** Yes, requires network (Crossref, arXiv) unless everything is cached. If the ingest command's `--no-network` option is set:
- if a manifest already exists on disk and `--force` is not set, return the existing manifest without network access
- otherwise, return a clear error indicating which reference(s) require network

**Example:** `erdos ingest 42 --json` might output for each reference: metadata plus local_path if downloaded.

#### 5. Index building (`erdos search --build-index`)

Build or update the search index. In v1, this is exposed via `erdos search --build-index` rather than a dedicated `erdos index build` command.

**Behavior (v1.1):**
- Builds/rebuilds a local SQLite FTS5 index for **problem content** (statements/notes).
- Literature extract indexing is deferred (see Spec 014 and related future work).

**Output (v1.1):** Progress messages are written to stderr. In `--json` mode, stdout is reserved for the final `CLIOutput` JSON.

**Exit codes:** 0 on success, nonzero on failure.

**Example:** `erdos search --build-index "prime number"` (builds if needed, then queries).

#### 6. `erdos search "<query>"`

Search the index for a query string.

**Behavior:** Performs a keyword search against the local BM25 index (SQLite FTS5). Vector search is deferred until after the v1 BM25 pipeline is stable.

**Output (v1.1):**
- Human: a list of snippet results (with highlighting when using FTS).
- JSON: `CLIOutput` envelope with `data.results[]` including `chunk_id`, `snippet`, `score`, `source_type`, `problem_id`, and `title`.

**Parameters (v1.1):** Supports `--limit` and optional `--problem` filter; `--build-index` rebuilds the index before searching.

**No new network calls (uses local index).**

**Example:** `erdos search "prime number long arithmetic progression"` might return relevant chunks with citations.

#### 7. `erdos ask <problem_id> "<question>"`

Ask a question about a specific problem, get a citation-grounded answer.

**v1.1 SSOT:** `docs/_archive/specs/spec-011-ask-command.md`.

**Behavior (v1.1):**
- Retrieves relevant sources from the local search index (problem content in v1.1).
- Builds a deterministic prompt (problem + retrieved sources + question).
- Optionally executes an external LLM subprocess (configurable; can be disabled with `--no-llm`).

**Output (v1.1):** Human mode prints the answer. JSON mode returns a `CLIOutput` envelope containing the prompt, answer (or `null` in `--no-llm` mode), and a `sources[]` array.

#### 8. `erdos lean init`

Set up the Lean 4 project (if not already).

**Behavior (v1.1):** Ensures the Lean project scaffold exists under `formal/lean/` and validates required tooling. If `lake` is missing, it returns a structured error with instructions.

**Output:** Confirmation that Lean project is ready.

**Idempotent:** Running again should just verify everything is up to date.

#### 9. `erdos lean check <file.lean>`

Compile a Lean file (or the whole project) and report errors.

**Behavior:** Runs `lake build <module>` (derived from the file path, e.g. `Erdos/Problem006.lean` → `Erdos.Problem006`). Captures and parses error messages.

**Output:** If errors, print them nicely. JSON output provides structured error objects. If successful, output "OK".

**Exit codes:** 0 if no errors, nonzero (e.g. 5) if Lean compile error.

#### 10. `erdos lean formalize <problem_id>`

Generate a Lean skeleton for the given problem.

**Behavior:** Reads the problem statement and creates a Lean file with:
- Problem statement in comments
- Necessary imports
- Placeholder theorem with `sorry`

**Output:** Creates `Problem<id>.lean`. Outputs file path confirmation.

#### 11. `erdos loop <problem_id>`

Run an interactive (or automated) loop of Lean proof attempts using an LLM agent.

**Behavior:** Orchestrates an iterative process:
1. Ensure Lean environment is ready
2. Load target problem's Lean file
3. If file has `sorry`, use LLM to attempt to fill them
4. Run `erdos lean check`, get errors, feed to LLM for fix suggestions
5. Apply changes, repeat
6. Log every iteration

**Status:** Deferred to v1.2+ (SPEC-012). Not implemented in v1.1.

**Output:** Stream the process in human mode. JSON output references log file.

**Exit codes:** 0 if proof completed, different codes for "gave up" vs error.

### Global Flags and Behavior

Global flags implemented in v1.1 (SSOT: `src/erdos/cli.py`): `--json`, `--log-level`, `--version`.

### Error Model and JSON Failure Outputs

Structured error JSON for `--json` mode:

```json
{
  "schema_version": 1,
  "command": "erdos show",
  "success": false,
  "data": null,
  "error": { "type": "NotFound", "message": "Problem 9999 not found", "code": 3 },
  "timestamp": "2026-01-01T00:00:00Z",
  "duration_ms": 0
}
```

### Command Contract for Automation

- **Stable JSON schemas:** Each command's JSON output includes `"schema_version": 1` and `"command": "erdos <name>"`
- **Versioning:** `erdos --version` yields semantic version
- **Consistency:** Fields like `id` vs `problem_id` will be consistent
- **No mixing human text in JSON:** JSON mode prints only the JSON object/array

---

## 5) Vertical Slice Roadmap (End-to-End, Must Work)

**Objective:** Achieve an end-to-end demonstration on a small target problem, verifying each step of the harness pipeline.

### Step-by-Step Plan

#### 1. Setup and Data Load

```bash
git clone ... && cd erdos-banger && git submodule update --init
erdos list --status open --limit 1
```

**Milestone:** Basic CLI and data import working.

#### 2. Select a Target Problem

```bash
erdos show X
```

**Milestone:** `show` displays correct info from dataset.

#### 3. Ingest References

```bash
erdos ingest X
```

Triggers:
- Crossref metadata fetch for DOI references
- arXiv metadata fetch + source tarball caching for arXiv references
- Best-effort plain-text extract from the largest `.tex` file (for future indexing)
- Save a portable manifest file (relative paths, deterministic hashes)
- (v2.0+) Optional PDF conversion via Marker (Spec 019)

**Verification:** `literature/manifests/X.yaml` exists with proper structure.

**Milestone:** External integration works.

#### 4. Build Index

```bash
erdos search --build-index "keyword"
```

**Verification:** Search returns snippets from problem statements/notes. Ingested paper extracts are cached for future indexing and will not appear in search results until a later indexing spec adds reference chunk indexing.

**Milestone:** Functional retrieval.

#### 5. Ask a Question

```bash
erdos ask X "What is known about this problem?"
```

**Milestone:** Citation-rich answer produced.

#### 6. Formalize Definition Skeleton

```bash
erdos lean formalize X
erdos lean check Erdos/ProblemX.lean
```

**Milestone:** Lean integration works.

#### 7. Lean/LLM Loop

Demonstrate capturing Lean errors and responding to them.

**Milestone:** Harness can capture Lean errors and respond.

#### 8. Logging & Reproducibility

Verify log file created with:
- Command sequence, time, model name
- Each retrieval with query and results
- Lean results and LLM prompts
- Commit hash of repo and submodule

**Milestone:** Logging is complete.

### Vertical Slice One-Liner

```bash
erdos ingest 295 && erdos search --build-index "keyword" && erdos ask 295 "What's the status?" && erdos lean formalize 295 && erdos lean check Erdos/Problem295.lean
```

---

## 6) Horizontal Slice Roadmap (Scale Plan)

### Scale to All Problems

- Handle ~1135 problems
- Add batch mode: `erdos ingest --all-open --max-prize 1000`
- Rate-limit obeying (3s between Crossref calls)
- Prioritize problems with known results or prizes

### Multiple Source Types

Extend beyond arXiv:
- Semantic Scholar API
- OpenAlex (CC0 data)
- CORE (core.ac.uk)
- zbMATH Open

### Better Retrieval

- Add reranker model
- Incorporate problem metadata in retrieval
- Evaluate retrieval qualitatively

### Lean Automation Enhancements

- Create common library of definitions
- Introduce Lean tactics in the loop
- Use LeanDojo if beneficial
- Evaluate formalization progress

### Benchmark & Evaluation Suites

- Automated questions for solved problems
- Measure coverage

### Contributor Workflows

- Enforce coding standards via pre-commit
- CI for PRs
- Documentation for multiple personas

### Performance and Scaling Hardware

- Consider Postgres+pgvector for larger scale
- Dedicated vector DB like Qdrant

---

## 7) Stack + Dependencies (Minimal-to-Strong Path)

### Python Tooling

Python 3.11+. Use uv for dependency management (PEP 621 + dependency groups + `uv.lock`) and builds/publishing (`uv build`, `uv publish`).

### CLI Library

Use Typer (built on Click) with Rich for formatting.

### Database/Storage

**Default:** SQLite with FTS5

**For vectors:**
- Option 1: BLOB in SQLite with brute force search
- Option 2: faiss-cpu
- Option 3: numpy brute force, hnswlib for approximate
- Option 4: pgvector if user has Postgres
- Option 5: Qdrant (Apache 2.0)

**Minimal path:** Brute force with numpy.

### LLM/AI Dependencies

- OpenAI API (optional, requires API key)
- Focus on Claude Code environment for v1

### Document Conversion

**Primary (v2.0+):** Marker (GPL) - best quality for math PDF conversion with LLM enhancement.
- Supports multiple LLM backends: Gemini, Claude, OpenAI, Ollama
- See Spec 019 for configuration details

**Alternatives considered:**
- **Docling** (MIT) - blocked by Typer version conflict
- **GROBID** (AGPL) - problematic viral license
- **Nougat** - non-commercial license concerns
- **PyMuPDF** (AGPL) - prohibited by license policy

### Metadata Sources

**Architecture: Single Responsibility + Dependency Inversion**

```
┌─────────────────────────────────────────────────────────────┐
│                    erdos ingest <id>                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               MetadataProvider (Protocol/Port)              │
│  get_by_doi(doi) -> ReferenceRecord                         │
│  get_by_arxiv(arxiv_id) -> ReferenceRecord                  │
│  search(query) -> List[ReferenceRecord]                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  OpenAlex    │   │   arXiv      │   │  Crossref    │
│  (PRIMARY)   │   │  (SOURCE)    │   │  (FALLBACK)  │
│              │   │              │   │              │
│ • metadata   │   │ • LaTeX/TeX  │   │ • If OA fails│
│ • citations  │   │ • HTML       │   │ • Direct DOI │
│ • topics     │   │ • Abstract   │   │   lookup     │
│ • deduped    │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
```

**Role Assignments (Rob C. Martin SRP):**

| API | Role | When to Call |
|-----|------|--------------|
| **OpenAlex** | **Primary metadata source** | Always first for DOI/title/author/abstract/citations |
| **arXiv** | **Source content provider** | When we need LaTeX/TeX for extraction (content, not metadata) |
| **Crossref** | **Fallback only** | If OpenAlex returns nothing (rare edge cases) |

**Why OpenAlex as Primary:**
1. **Already aggregates Crossref** - calling both is redundant
2. **Built-in deduplication** - matches arXiv preprint ↔ journal version
3. **Richer metadata** - citations, topics, concepts, institutions
4. **Better rate limits** - 100k/day vs Crossref's polite pool
5. **100% open** - CC0 license, no auth required

**Secondary (Source Content):**
- arXiv API (for LaTeX source, HTML) - 1 req/3s rate limit
- Used for content acquisition, NOT metadata lookup

**Future/Optional (Good Redundancy - adds NEW information):**
- Semantic Scholar - citation context extraction (who cites what and why)
- Exa Research API - natural language research synthesis, agentic queries
- zbMATH Open - math-specific metadata not in general databases
- CORE - institutional repositories
- Unpaywall (100k/day with email) - open access PDF locations

### Lean Tools

- **elan:** Users install it
- **mathlib4:** Pinned in lakefile
- **LeanDojo/Pantograph:** Future consideration

### Licensing Summary

- **Core dependencies:** permissive only (MIT/BSD/Apache)
- **Optional extras:** may include GPL if no permissive alternative exists
  - `[pdf]` extra: Marker (GPL) - best quality for math PDF conversion
  - Rationale: GPL is acceptable only as an opt-in extra; distributing builds that include it must comply with GPL obligations (core remains permissive)
- **Lean and mathlib:** Apache 2.0
- **Data sources:** OpenAlex (CC0), arXiv (various), Crossref (open metadata)

**Policy:** We prefer MIT/Apache for everything. GPL is acceptable ONLY for optional extras where:
1. No permissive alternative exists with equivalent quality
2. The feature is not required for core functionality
3. Users must explicitly opt-in via `uv sync --extra <name>`

---

## 8) Claude Code / Codex Harness Integration

### Makefile / Justfile for Claude/Codex

Example Make targets:
- `make ingest-all-open`
- `make demo`
- `make lean-check-all`
- `make update-dataset`
- `make format`

### Project-Local Claude Skills

Six skills in `.claude/skills/`:

#### 1. `add_problem_note.SKILL.md`

**Description:** "When the user asks to record a finding or note about an Erdős problem, use this skill."

**Content:** Instructs how to record new information, suggesting upstream PR or local tracking.

#### 2. `triage_literature.SKILL.md`

**Description:** "Helps classify and structure references for a problem."

**Content:** Instructions for handling new references, running appropriate harness commands.

#### 3. `generate_lean_skeleton.SKILL.md`

**Description:** "When asked to formalize or create Lean definitions for a problem, do it."

**Content:** Instructions for reading problem statements and producing Lean code with proper structure.

#### 4. `interpret_lean_errors.SKILL.md`

**Description:** "When Lean compilation fails, help debug."

**Content:** Triggers on Lean error messages, provides analysis and fix suggestions.

#### 5. `run_repro_loop.SKILL.md`

**Description:** "Coordinates multiple iterations of propose-check-fix for proofs, ensuring logs."

**Content:** Guide for iterative proof attempts with proper logging.

#### 6. `contributor_policy.SKILL.md`

**Description:** "Ensures AI assistant follows contributor guidelines and legal constraints."

**Content:** Enforces policies: cite sources, don't share full content, follow license guidelines.

### MCP Upgrade Path (Optional)

Tool names and signatures:
- `search_index(query: str)` → search results
- `get_problem(id: int)` → ProblemRecord
- `get_refs(id: int)` → ReferenceRecords
- `run_lean(file: str)` → status and errors
- `log_run(entry: dict)` → success

Example config:
```json
"mcpServers": {
   "erdos": { "command": "erdos-mcp", "args": [] }
}
```

---

## 9) Legal/Licensing Policy

### Repository License

Apache-2.0 (to match erdosproblems dataset).

### What Is Stored in Git

- The erdosproblems dataset (Apache 2.0)
- Processed metadata manifests
- Short excerpts in logs/answers (fair use)
- Lean formalizations

### What Is Not Stored (Gitignored)

- Full texts of papers
- Third-party copyrighted material
- User's private data (API keys, etc.)

### Use of arXiv Content

- Respect rate limits (1 req/3s)
- Always cite arXiv ID or DOI
- Don't redistribute PDFs beyond ephemeral usage

### Citations in Generated Content

- Always cite with `【source†Lx-Ly】` format
- Don't output full text of papers

### Rate Limiting & Courtesy

- Custom User-Agent string
- Include email in Unpaywall requests
- Respect rate limit headers

---

## 10) Init Commands (Paste-and-Run)

### a. Repository Initialization

```bash
# 1. Clone the harness repo
git clone https://github.com/youruser/erdos-banger.git
cd erdos-banger

# 2. Initialize submodule for Erdős problems data
git submodule update --init --recursive
```

### b. Python Environment Setup

```bash
# 3. Install uv (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Install dependencies into .venv (uses uv.lock)
uv sync
```

Or via pipx:
```bash
pipx install 'erdos-banger==0.1.0'
```

### c. Verify CLI and Version

```bash
uv run erdos --version
# Should output: erdos-banger 0.1.0

uv run erdos list --help
# Should show usage help
```

### d. Lean Installation via elan

```bash
# 5. Install Lean using elan (if not already installed)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Follow prompts to add to PATH
```

### e. Initialize Lean Project

```bash
# 6. Set up Lean project and mathlib
erdos lean init
```

### f. Quick "Hello World" Lean Check

```bash
erdos lean formalize 1
erdos lean check Erdos/Problem001.lean
```

### g. Try an End-to-End Mini-Run

```bash
erdos refs 1           # see what references problem 1 has pre-ingest
erdos ingest 1 --no-network  # should succeed only if a manifest already exists; otherwise error (tests error handling)
erdos search "keyword"
```

---

## 11) First 15 GitHub Issues (Real Build Plan)

### 1. CLI Scaffold and Config (#1)

**Description:** Set up basic CLI structure using Typer. Implement global flags and config file parser.

**Acceptance:** Running `erdos --help` shows usage. Config precedence tested.

### 2. Import Erdős Problems Data (#2)

**Description:** Write loader for `data/problems_enriched.yaml` (v1 enriched dataset). Detect upstream metadata-only `data/erdosproblems/data/problems.yaml` and fail with a clear error if titles/statements are missing. Create Pydantic models.

**Acceptance:** `erdos list` prints total count. `erdos show <id>` displays correct info.

### 3. `erdos list` Filtering (#3)

**Description:** Implement filters (status, prize range, tags).

**Acceptance:** Unit tests pass for filtering.

### 4. Reference Listing and Manifest Structure (#4)

**Description:** Implement `erdos refs`. Design manifest schema.

**Acceptance:** `erdos refs <id>` displays references. Manifest class ready.

### 5. Metadata Fetch (Crossref/ArXiv) (#5)

**Description:** Implement functions to fetch reference metadata.

**Acceptance:** Given a known DOI, code fetches title and authors.

### 6. Download & Conversion Pipeline (#6)

**Description:** Implement arXiv source download + best-effort extraction (v1.1). PDF conversion is deferred to Spec 019 (Marker, v2.0+).

**Acceptance:** On sample arXiv paper, produces extracted text file.

### 7. `erdos ingest` Command Flow (#7)

**Description:** Tie together metadata fetch and conversion.

**Acceptance:** Running twice is idempotent. Manifest file matches expected fields.

### 8. Search Index (SQLite FTS5) (#8)

**Description:** Define SQLite tables with FTS5 virtual table.

**Acceptance:** After ingesting, `erdos search --build-index "<query>"` creates/updates the SQLite index file.

### 9. Vector Embeddings and Hybrid Search (#9)

**Description:** Integrate embedding model. Implement combining lexical and semantic results.

**Acceptance:** Semantic search picks up related but non-lexical matches.

### 10. `erdos search` Output & Citation Format (#10)

**Description:** Implement formatting of search results with snippets and citations.

**Acceptance:** JSON output structure matches spec.

### 11. Q&A with Citations (`erdos ask`) (#11)

**Description:** Implement retrieval and templating for Q&A.

**Acceptance:** Returns structured answer with citations (even if stubbed).

### 12. Lean Project Initialization (`erdos lean init`) (#12)

**Description:** Write Lakefile and lean-toolchain generation.

**Acceptance:** `formal/lean` directory exists with lakefile after running.

### 13. Lean Check and Parse Errors (`erdos lean check`) (#13)

**Description:** Run lean, capture stderr, parse error format.

**Acceptance:** Known faulty Lean file produces structured error output.

### 14. Formalize Skeleton (`erdos lean formalize`) (#14)

**Description:** Implement basic skeleton generation.

**Acceptance:** Produced Lean file compiles with `sorry`.

### 15. Logging System & Test (#15)

**Description:** Implement logging to file for commands.

**Acceptance:** Log file created after running commands with proper entries.

---

## Bonus: First Target Problem Set (for V1 Testing)

### Selection Criteria

- Small & self-contained
- Well-documented with accessible literature
- Formalization-friendly
- Coverage across major tag families

### Suggested 10 Problems (Metadata-Verified)

These are suggested IDs to seed v1 development. Titles/statements are not present in upstream metadata and must come from `data/problems_enriched.yaml` (Spec 005).

Source for metadata below: `teorth/erdosproblems` `data/problems.yaml` (pin via submodule for reproducibility).

| Problem | Upstream `status.state` | Upstream `prize` | Upstream `formalized.state` | Upstream `tags` |
|--------:|--------------------------|------------------|------------------------------|-----------------|
| 4 | proved | $10000 | yes | number theory, primes |
| 6 | proved | $100 | yes | number theory, primes |
| 67 | proved | $500 | yes | discrepancy |
| 123 | open | $250 | yes | number theory |
| 148 | open | no | no | number theory, unit fractions |
| 295 | open | no | yes | number theory, unit fractions |
| 316 | disproved (Lean) | no | yes | number theory, unit fractions |
| 476 | proved (Lean) | no | no | number theory, additive combinatorics |
| 707 | disproved (Lean) | $1000 | yes | additive combinatorics, sidon sets |
| 728 | proved (Lean) | no | yes | number theory, factorials |

### Summary of Criteria

- **Solved/disproved** problems validate reporting, status handling, and Lean-related tooling.
- **Open** problems validate search and enrichment workflows.
- **Mixed tags** validate filtering and display logic across domains.
