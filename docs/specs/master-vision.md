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

Handles reference material for a given problem. For each problem or reference, the harness can fetch metadata (Crossref, OpenAlex, etc.) and open-access content (via arXiv, Unpaywall, CORE, etc.) if legally available. Instead of storing PDFs, it records manifests: JSON or YAML listing each source with metadata, URL, and cache status. Full texts are only stored in a private cache if permitted (e.g. arXiv HTML or source) and are not checked into git.

### Storage Layer (Metadata + Cache)

Uses a local database (default SQLite for simplicity) to store structured metadata: problem records, reference metadata, chunked text, vector embeddings, etc. For v1, SQLite with FTS5 provides a lightweight full-text index. A separate local folder (e.g. `literature/cache/`) holds cached content like arXiv source or HTML, and possibly pre-processed text, keyed by content hashes/IDs. Nothing that violates licenses will be stored in git; the cache is user-local and git-ignored (see Legal Policy).

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
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐    │
│   │ problems.yaml   │      │ Crossref        │      │ arXiv           │    │
│   │ (metadata SSOT) │      │ OpenAlex        │      │ Unpaywall       │    │
│   └────────┬────────┘      │ Semantic Scholar│      │ CORE            │    │
│            │               └────────┬────────┘      └────────┬────────┘    │
│            │                        │                        │             │
└────────────┼────────────────────────┼────────────────────────┼─────────────┘
             │                        │                        │
             v                        v                        v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐    │
│   │ Problem DB      │      │ Search Index    │      │ Literature      │    │
│   │ (SQLite)        │      │ (SQLite FTS5)   │      │ Cache           │    │
│   │                 │      │                 │      │                 │    │
│   │ • problems      │      │ • text chunks   │      │ • manifests/    │    │
│   │ • references    │      │ • vectors       │      │ • cache/        │    │
│   │ • metadata      │      │ • embeddings    │      │ • extracts/     │    │
│   └────────┬────────┘      └────────┬────────┘      └────────┬────────┘    │
│            │                        │                        │             │
└────────────┼────────────────────────┼────────────────────────┼─────────────┘
             │                        │                        │
             └────────────────────────┼────────────────────────┘
                                      │
                                      v
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI COMMANDS                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Info Display        Ingestion           Search/Q&A         Formalization │
│   ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐   │
│   │ list      │      │ ingest    │      │ search    │      │ lean init │   │
│   │ show      │      │ index     │      │ ask       │      │ lean check│   │
│   │ refs      │      │           │      │           │      │ lean form │   │
│   └───────────┘      └───────────┘      └───────────┘      │ loop      │   │
│                                                            └─────┬─────┘   │
│                                                                  │         │
└──────────────────────────────────────────────────────────────────┼─────────┘
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

**Data Flow:**
1. **Import** → Problem dataset loads into SQLite, external APIs enrich references
2. **Index** → Text chunks + embeddings populate FTS5 search index
3. **Query** → CLI commands read/write to storage, invoke Lean compilation
4. **Iterate** → Lean errors feed back to LLM loop, all steps logged

**Diagram Summary:** The dataset feeds the problem DB. Ingestion fetches references (via external APIs) into manifests and possibly cached text. An index builder uses the DB content (problem statements, reference texts) to create a hybrid search index (text + vectors). The CLI commands orchestrate these: e.g., `erdos search` queries the index and returns relevant text chunks with citations; `erdos ask` uses LLM (via CLI integration) to answer questions with those citations. The Lean project is initialized by `erdos lean init` and contains Lean files. Commands like `erdos lean formalize` create a Lean stub for a problem, and `erdos loop` runs an iterative loop where the LLM proposes proofs, Lean checks them, and feedback is logged. Logging happens throughout to enable reproducibility and evaluation.

---

## 3) Repo Structure

Below is a proposed repository file tree. Directories are marked with a trailing `/`. We indicate which parts are committed to git and which are user-local (ignored or generated).

```
erdos-banger/
├── README.md                   # Project overview, setup, basic usage (committed)
├── LICENSE                     # Project license (committed, Apache-2.0)
├── pyproject.toml              # PEP 621 project config (committed)
├── uv.lock                     # Locked dependencies (committed)
├── .python-version             # Dev Python pin (committed)
├── src/                        # Python package source (committed)
│   └── erdos/
│       ├── __init__.py
│       ├── cli.py              # Typer entry point (committed)
│       ├── commands/           # Implementation of each subcommand (committed)
│       │   ├── list_cmd.py, show.py, refs.py, ingest.py, ... (committed)
│       ├── core/               # Core library (committed)
│       │   ├── problem_loader.py   # Loads YAML from dataset (committed)
│       │   ├── search_index.py     # Builds/queries SQLite FTS (committed)
│       │   ├── lean_runner.py      # Runs Lake/Lean, parses errors (committed)
│       │   ├── ingest_refs.py      # Metadata fetch & conversion (committed)
│       │   └── models.py           # Pydantic models (committed)
│       ├── agents/             # (Optional) LLM agent wrappers (deferred)
│       │   └── loop_agent.py
│       └── py.typed            # PEP 561 marker (committed)
├── data/                       # Problem dataset (upstream + local enrichments)
│   ├── problems_enriched.yaml  # Enriched v1 dataset (titles/statements) (committed)
│   └── erdosproblems/          # teorth/erdosproblems submodule (not our code)
│       ├── data/problems.yaml  # Upstream metadata-only dataset (not modified)
│       └── ...                 # other files from the dataset
├── literature/
│   ├── manifests/              # Metadata manifests for references (committed or generated)
│   │   ├── 0001.yaml           # Example: references for problem #1 (committed after ingest)
│   │   └── ...
│   ├── cache/                  # Fulltext cache (not in git, user local)
│   │   ├── arxiv_1234567v1.pdf # example cached PDF (if legally allowed, otherwise not present)
│   │   ├── arxiv_2201.00001.tar.gz # cached arXiv source if OA (not committed)
│   │   └── ...
│   └── extracts/               # Processed text extracts (e.g., markdown/HTML of papers) (git-ignored, can be regenerated)
│       └── 0001_ref1.txt       # e.g. text of first reference for problem 1
├── index/
│   ├── erdos.sqlite            # SQLite database with FTS index and metadata (built) (git-ignored)
│   ├── index.cfg               # Index configuration (committed, e.g. embedding model used)
│   └── pgvector.sql            # (Optional) schema for Postgres if used (committed)
├── formal/
│   └── lean/                   # Lean4 project root (committed)
│       ├── lean-toolchain      # Lean version (e.g. leanprover/lean4:v4.12.0) (committed)
│       ├── lakefile.lean       # Lake configuration (committed)
│       ├── .lake/              # Lake deps/build artifacts (git-ignored)
│       ├── Erdos/              # Our Lean files for each problem (committed)
│       │   ├── Problem001.lean # auto-generated skeleton for problem 1 (committed)
│       │   ├── Problem001ProofAttempts.lean # iterative attempts (committed)
│       │   └── ...
│       └── build/              # Build artifacts (.olean files etc.) (git-ignored)
├── .claude/
│   └── skills/                 # Claude Code project-local skills (committed)
│       ├── add_problem_note.SKILL.md        # Skill 1
│       ├── triage_literature.SKILL.md       # Skill 2
│       ├── generate_lean_skeleton.SKILL.md  # Skill 3
│       ├── interpret_lean_errors.SKILL.md   # Skill 4
│       ├── run_repro_loop.SKILL.md          # Skill 5
│       └── contributor_policy.SKILL.md      # Skill 6
├── scripts/
│   ├── init_repo.sh            # Bash script for initial setup (submodule init, etc.) (committed)
│   ├── ingest_all.sh           # Example script to ingest all open problems (committed)
│   └── ...
├── logs/
│   ├── run_20260116_103000Z.yaml    # Sample log of a full run (timestamped) (git-ignored)
│   ├── lean_errors_Problem001.json  # Extracted Lean errors for problem 1 (git-ignored)
│   └── ...
├── docs/
│   ├── architecture.md         # More detailed architecture notes (committed)
│   ├── user-guide.md           # Usage instructions (committed)
│   ├── contributor-guide.md    # For open-source contributors (committed)
│   ├── legal.md                # Licensing and data policy (committed)
│   └── evaluation.md           # Plan for metrics and testing (committed)
└── tests/
    ├── test_cli_basic.py       # Basic tests for CLI outputs (committed)
    ├── test_ingest.py          # Tests for ingestion logic (with sample data) (committed)
    ├── test_search.py          # Tests for search indexing and querying (committed)
    ├── test_lean.py            # Tests for Lean integration (mocking lean if needed) (committed)
    └── ...
```

### What's Committed vs Ignored

**Committed:**
- All code (CLI, core logic, model schemas, docs), config, and small metadata like manifests and Lean source files
- The erdosproblems dataset (as a submodule to keep it separate but versioned)
- Structured manifests (YAML/JSON listing reference metadata) – these contain DOIs, arXiv IDs, etc., but not full paper text
- Lean files and their updates (this is part of our work product)
- The `.claude/skills` (project-specific LLM skills) are committed so that they can be shared and versioned

**Git-ignored:**
- Any large or non-redistributable data, including:
  - The literature fulltext cache (`literature/cache/`)
  - Any extracted full texts (`literature/extracts/`)
  - Search index files and databases (`index/` contents except config)
  - Lean build artifacts (`formal/lean/build/` and the downloaded mathlib library)
  - Run logs
- These are either generated or user-specific. We provide ways to regenerate from source metadata when possible. For example, a collaborator can run `erdos ingest 1` to fetch and parse references for problem 1 if they have network access, rather than storing those bulky files in git.

**Data submodule strategy:** Include `teorth/erdosproblems` via a git submodule pinned to a specific commit (reproducible metadata). Treat `data/erdosproblems/` as external upstream data.

### Schema & Model Files

We'll have Pydantic models in `src/erdos/core/models.py` (see Spec 003) for key entities:

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

- Non-interactive by default (no prompts unless `--yes` for confirmations)
- Returns exit code 0 on success, nonzero on failure (different codes for different failure types)
- Accepts `--json` to output machine-readable JSON (with a defined schema and version)
- All commands respect global flags:
  - `--config` (point to a config file)
  - `--cache-dir` (override default cache location)
  - `--log-level` (e.g. DEBUG/INFO/WARN/ERROR)
  - `--trace` (very verbose logging including tool invocations)
  - `--no-network` (disallow any network calls; commands will fail if they require network)
  - `--resume` (where applicable, resume from last checkpoint)
  - `--yes`/`--no-input` (assume yes or no for any prompts, though by default we try not to have prompts)

### Commands and Usage

#### 1. `erdos list [filters]`

List problems with optional filters. This reads the problem data (from the YAML or our imported JSON).

**Filters:**
- `--status` (e.g. open/proved/disproved)
- `--prize` (yes/no or min-max prize amount)
- `--tag` (match one or multiple tags, e.g. `--tag "number theory"`)

For instance, `erdos list --status open --prize-min 1000` lists open problems with prize ≥ $1000.

**Output:** In human mode, a table with columns: ID, prize, status, title (shortened), maybe tags. In JSON, an array of ProblemRecords (with id and summary fields).

**Exit codes:** 0 if results found (even if empty list), 0 as well if no results (but maybe we differentiate by a message). Nonzero only if an error (e.g., dataset not found). Possibly use exit code 2 to indicate "no results" vs 1 for general error.

**No network required.**

**Example:** `erdos list --status open --tag "graph theory"` might output a filtered list. If `--json`, it outputs JSON list of problems.

#### 2. `erdos show <problem_id>`

Show detailed info for a single problem.

**Input:** A problem ID or number (like `erdos show 42`).

**Behavior:** Loads that problem from the dataset. Outputs the full problem statement, status, prize info, tags, and references list. Essentially a nicely formatted view of the YAML entry.

**In JSON:** Returns a full ProblemRecord JSON (including list of reference keys/IDs but not the actual reference metadata, which might not be loaded yet until ingestion).

**No network.**

**Errors:** Nonzero exit if problem_id not found (exit code e.g. 3 for "not found").

**Example:** `erdos show 100 --json` → outputs JSON like:
```json
{
  "schema_version": 1,
  "command": "erdos show",
  "success": true,
  "data": {
    "id": 100,
    "title": "...",
    "statement": "...",
    "status": "open",
    "prize": 0,
    "tags": ["number theory"],
    "references": [{"key": "Erdos1975", "citation": "..."}],
    "oeis_ids": [],
    "notes": null,
    "formalized": false
  },
  "error": null
}
```

In human output, could show a markdown-like output (title, statement, references enumerated).

**Contract:** Stable fields in JSON so that external tools (or LLM agents) can parse problem details easily.

#### 3. `erdos refs <problem_id>`

List references for a problem, with available metadata.

**Behavior:** Lists `ProblemRecord.references` from the enriched problems YAML. The upstream `teorth/erdosproblems` `data/problems.yaml` is metadata-only and does not contain reference lists. For v1, `erdos refs` is YAML-only (no API enrichment).

If ingestion was run (see next command), we can enhance output with fetched metadata (like actual titles, DOIs, etc.). Possibly `refs` triggers an ingest if none exists, or we separate concerns: `refs` just shows what's in the dataset, and `ingest` must be called to fetch details. A compromise: `refs` could check if a manifest exists (e.g. `literature/manifests/0001.yaml` for problem 1) and if not, print "(metadata not ingested)".

**Output:** Numbered list of references. For example:
1. Paul Erdős (1975), Some old and new problems in combinatorial number theory. J. Number Theory etc (with DOI if available).

Or a placeholder if minimal info. JSON output would give an array of ReferenceRecords (with available fields; if not ingested, just what we know like author/title string).

**Network:** Not needed if already ingested; if not ingested, we don't fetch automatically unless `--ingest` flag is passed for convenience. Keep `refs` read-only by default.

**Example:** `erdos refs 42` might list "(No references listed)" if none in dataset, or a few references. If `--json`, list objects with known keys (maybe containing doi or arxivId if present in YAML).

#### 4. `erdos ingest <problem_id>`

Ingest (fetch) reference data for a problem. This is a key step involving external APIs, and may be interactive or lengthy.

**Behavior:** Looks up each reference associated with the problem:
- If a reference has a DOI, use Crossref API to get full citation
- If it has an arXiv ID, use arXiv API to get metadata (title, authors, etc.)
- If references are only described textually, attempt to find them via search (Crossref title search, or OpenAlex by title & author)
- Use Unpaywall to find open access links (Unpaywall recommends including an email and allows ~100k/day)

For each reference:
- Create a ReferenceRecord with metadata
- If an open-access PDF or arXiv source is available, download it to `literature/cache/` (only if legally allowed: e.g. if Unpaywall says there is an open repository PDF, or arXiv PDF which is CC BY). For arXiv: since Dec 2023, arXiv provides HTML for TeX submissions, which we prefer to download (or the TeX source via arXiv API's e-print if needed). We avoid downloading publisher PDFs unless clearly open (e.g. Creative Commons).
- If PDF is downloaded, run a conversion pipeline: first preference is arXiv HTML or LaTeX. If not arXiv, use Docling or similar to convert PDF to Markdown/HTML, preserving math via MathML or LaTeX. (Docling is a candidate optional dependency; as of 2026-01 it is not included in v1 due to a Typer version conflict.)
- Save a manifest file `literature/manifests/<id>.yaml` with all reference entries and a summary of their status. Include checksums (e.g. MD5 of PDF/TeX) for reproducibility.

**Output:** In human mode, print a summary: e.g. "Fetched 3 references. 2 PDFs downloaded (1 via arXiv, 1 via Unpaywall), 1 metadata only." JSON output would detail each reference and what happened.

**Idempotence:** Running `erdos ingest` again should skip already ingested references unless a `--force` is given to refresh.

**Network:** Yes, requires network (Crossref, etc.) unless everything is cached. If `--no-network` flag is set, it will error out. If `--resume` is provided, we resume a previously interrupted ingestion.

**Example:** `erdos ingest 42 --json` might output for each reference: metadata plus local_path if downloaded.

#### 5. `erdos index build`

Build or update the search index.

**Behavior:**
- Ensure the SQLite (or Postgres) DB is set up (if not, create schema)
- Insert/update Problem texts: the problem statements themselves can be searchable content
- Insert reference texts: For each reference that has an extracted text, break into chunks (maybe 200-300 words per chunk). Store each chunk with a link to the reference. Use SQLite FTS5 to index the text. Also compute an embedding for each chunk using a chosen model (perhaps sentence-transformers or similar).
- Save the index

**Output:** Human mode: some stats – "Indexed 50 problems and 120 references (980 chunks). FTS terms: ~10k, vector dim: 384." JSON: could output summary stats with counts.

**Exit codes:** 0 on success, nonzero on failure.

**Example:** `erdos index build` (no args needed, uses config for which model etc.).

#### 6. `erdos search "<query>"`

Search the index for a query string.

**Behavior:** Performs a keyword search against the local BM25 index (SQLite FTS5). Vector search is deferred until after the v1 BM25 pipeline is stable.

**Output:** In human mode, a list of snippet results. JSON output: an array of RetrievedChunk objects.

**Parameters:** Could support `--top-k 10` to adjust number of results.

**No new network calls (uses local index).**

**Example:** `erdos search "prime number long arithmetic progression"` might return relevant chunks with citations.

#### 7. `erdos ask <problem_id> "<question>"`

Ask a question about a specific problem, get a citation-grounded answer.

**Behavior:** (v1.1+) Invokes an LLM via the local environment (Claude Code workflow). Runs retrieval-augmented generation:
- Searches the index with a query composed of [problem context + question]
- Constructs a prompt for the LLM including retrieved snippets with citations
- Post-processes the answer to ensure citations are properly numbered

**Output:** A nicely formatted answer with citations. JSON mode provides answer text and a `sources` array.

**Network:** Possibly required for LLM API call.

**Example:** `erdos ask 100 "What partial results are known?"` returns a summary with citations.

#### 8. `erdos lean init`

Set up the Lean 4 project (if not already).

**Behavior:** Initialize `formal/lean/` as a Lean project. Handle dependency setup: ensure elan is installed, run `lake update` to fetch mathlib4, etc.

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

**Safety:** Limit to N iterations or require user confirmation each step unless `--yes`.

**Output:** Stream the process in human mode. JSON output references log file.

**Exit codes:** 0 if proof completed, different codes for "gave up" vs error.

### Global Flags and Behavior

- `--config`: Specify a config file (YAML/JSON)
- `--cache-dir`: Override default location
- `--log-level`: default INFO, DEBUG/TRACE available
- `--no-network`: Ensures no command will unexpectedly hit the internet
- `--resume`: Continue where left off
- `--yes`/`--no-input`: Control interactive prompts

### Error Model and JSON Failure Outputs

Structured error JSON for `--json` mode:
```json
{ "schema_version": 1, "command": "erdos show", "success": false, "data": null, "error": { "type": "NotFound", "message": "Problem 9999 not found", "code": 3 } }
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
- Crossref/OpenAlex query for each reference
- ArXiv PDF/HTML download if available
- Conversion via optional PDF tooling (Docling or similar)
- Save manifest file

**Verification:** `literature/manifests/X.yaml` exists with proper structure.

**Milestone:** External integration works.

#### 4. Build Index

```bash
erdos index build
```

**Verification:** Quick search query returns snippets from ingested content.

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
erdos ingest 295 && erdos index build && erdos ask 295 "What's the status?" && erdos lean formalize 295 && erdos lean check Erdos/Problem295.lean
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

**Docling:** MIT license, handles math and code. Candidate optional dependency (not included in v1 due to a Typer version conflict).

**Alternatives considered:**
- GROBID (AGPL - problematic license)
- Nougat (non-commercial license concerns)

### Metadata Sources

- Crossref REST API (open usage with limits)
- OpenAlex (100k/day)
- Unpaywall (100k/day with email)
- CORE
- zbMATH

### Lean Tools

- **elan:** Users install it
- **mathlib4:** Pinned in lakefile
- **LeanDojo/Pantograph:** Future consideration

### Licensing Summary

- Python libs: permissive (MIT/BSD/Apache)
- Docling (future optional): MIT
- Lean and mathlib: Apache2
- No GPL components included

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
erdos ingest 1 --no-network  # should error (tests error handling)
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

**Description:** Implement PDF/HTML download and conversion (Docling or similar; deferred until PDF tooling is added to the dependency set).

**Acceptance:** On sample arXiv paper, produces extracted text file.

### 7. `erdos ingest` Command Flow (#7)

**Description:** Tie together metadata fetch and conversion.

**Acceptance:** Running twice is idempotent. Manifest file matches expected fields.

### 8. Search Index (SQLite FTS5) (#8)

**Description:** Define SQLite tables with FTS5 virtual table.

**Acceptance:** After ingesting, `erdos index build` creates SQLite file.

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
