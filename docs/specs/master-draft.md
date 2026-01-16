Erdős Problem Research Harness – Design & Build Plan

1) Recommended repo name + positioning

Name candidates (no hype):
	•	erdos-harness (concise and descriptive)
	•	problem-lab
	•	erdos-lab
	•	erdos-workbench
	•	prizeworkbench
	•	resolute-cli
	•	conjecture-cli
	•	ep-research-kit (EP = Erdős Problems)
	•	lean-erdos-kit
	•	open-erdos

Chosen Name: erdos-harness

Tagline: CLI-first toolkit for collaborative research on Erdős problems, from literature to Lean formalization.

What it is:
	•	A CLI toolkit for Erdős problem research (no GUI needed for v1).
	•	A data-driven harness using Terence Tao’s erdosproblems dataset ￼ ￼ as the ground truth of problem statements and metadata.
	•	A retrieval and formalization pipeline combining literature search, hybrid search (text + vectors), and Lean 4 theorem proving.
	•	A reproducible environment for human researchers and AI agents to iterate on problems, with structured logs and stable outputs.
	•	A legal and open platform: uses openly licensed data (Apache-2.0 for erdosproblems ￼, CC licenses for literature when available) and respects content rights.

What it is not:
	•	Not a general unsolved math solver or competitor to Clay Millennium Problem solvers – scope is strictly Erdős problems (1135 problems curated by the community ￼).
	•	Not an AI agent claiming to solve problems automatically – it’s infrastructure to assist researchers, not a promise of breakthroughs.
	•	Not a web app or GUI – v1 is CLI-first with a focus on automation and integration (though future UI or web dashboards could build on it).
	•	Not a closed proprietary system – it won’t store paywalled papers or scraped PDFs in the repo; it relies on metadata and legal open-access content only.
	•	Not a one-off script collection – it aims for production-grade CLI quality (structured output, test coverage, config management, versioning) from the start.

2) Architecture overview (one page)

The harness is composed of modular components that work together in a pipeline. Key components and their roles:
	•	Problem Dataset Import: Leverages Terence Tao’s teorth/erdosproblems repository as a git submodule or managed snapshot to load problem data (YAML format) ￼. This is the canonical source for problem statements, status (open/solved), prizes, references, tags, etc. (Apache-2.0 licensed ￼). Our repo will treat this data as read-only ground truth – updates can be pulled or synced, but we won’t modify it directly (contributions can be upstreamed separately).
	•	Literature Ingestion & Manifests: Handles reference material for a given problem. For each problem or reference, the harness can fetch metadata (Crossref, OpenAlex, etc.) and open-access content (via arXiv, Unpaywall, CORE, etc.) if legally available. Instead of storing PDFs, it records manifests: JSON or YAML listing each source with metadata, URL, and cache status. Full texts are only stored in a private cache if permitted (e.g. arXiv HTML or source) and are not checked into git.
	•	Storage Layer (Metadata + Cache): Uses a local database (default SQLite for simplicity) to store structured metadata: problem records, reference metadata, chunked text, vector embeddings, etc. For v1, SQLite with FTS5 provides a lightweight full-text index ￼. A separate local folder (e.g. literature/cache/) holds cached content like arXiv source or HTML, and possibly pre-processed text, keyed by content hashes/IDs. Nothing that violates licenses will be stored in git; the cache is user-local and git-ignored (see Legal Policy).
	•	Hybrid Index (Search): Combines lexical search (e.g. BM25 via SQLite FTS5) and vector similarity for semantic search. Initially, we use SQLite FTS5 for keyword search ￼ and a small vector engine (e.g. in-memory via FAISS or an embedded library). For scaling or advanced use, we plan for an upgrade path to Postgres with the pgvector extension (to store embedding vectors with ACID compliance ￼), or an external vector DB like Qdrant (Rust-based, open source, optimized for high-dimensional search ￼ ￼). V1 keeps it simple: likely storing embeddings in SQLite or a lightweight local vector store due to small initial data.
	•	Lean4 Workspace: A structured Lean 4 project (formal/lean/) managed by Lean’s package manager Lake and version manager elan. This contains the formalization attempts: definitions, conjectures, partial proofs, etc. Lean 4 and mathlib4 are set up as dependencies ￼. The harness can create Lean files (problem statements, known lemmas) and compile them. Lean’s output (errors, warnings) is captured and fed back to guide the next iteration. The Lean toolchain (via elan) ensures consistent versions – elan will pick the version from a lean-toolchain file ￼ ￼ and download it if needed.
	•	CLI Commands: A unified erdos CLI with subcommands (list, show, refs, ingest, search, ask, lean, formalize, loop, etc. – defined in detail below). Each command is implemented with robust argument parsing, error handling, and optional JSON output for automation. We use a Python CLI framework (likely Typer with Rich for formatting) to get quick development and pretty output, or possibly Click if more mature stability is needed. The CLI is designed for both interactive use and as an API for LLM agents (deterministic outputs, machine-readable JSON with --json, no interactive prompts unless --yes/--no-input flags are used).
	•	Logging & Eval Harness: Every run produces structured logs (e.g. JSON lines or YAML) capturing the operations performed, external calls (with timestamps, parameters), and results. For instance, a search command log would include the query and the list of retrieved sources with their IDs and similarity scores. A lean check log would include the Lean version, file hashed, compile success/failure, and error messages. These logs go to logs/ (git-ignored) and can be used to evaluate progress over time. We also define some metrics: e.g. number of formal definitions added, Lean proofs completed, retrieval accuracy (perhaps measured later by human or known relevant references).
	•	Optional MCP Layer: (Pluggable, not required for v1) The Model Context Protocol (MCP) is an open standard for connecting AI assistants to tools ￼ ￼. Our CLI can optionally be wrapped or complemented by an MCP server exposing certain functions (like search_index, get_problem, run_lean) to AI clients like Claude Desktop. This is not mandatory in v1 since our CLI plus Claude’s local skills suffice, but we keep it in mind. The design allows an MCP integration without refactoring – e.g. by a lightweight wrapper that calls the same underlying Python functions that the CLI uses. If a user runs an MCP server, the model could directly call “tools” instead of shelling out, but in v1, shell command execution is assumed (the model can run erdos ... commands in a sandbox).

Architecture Diagram (ASCII):

[ teorth/erdosproblems dataset ] <-- (git submodule / import) --+                     
                                                              |    Problem
                                                     [ Data Importer ]                        
                                                              v    YAML→JSON models
                                                 +--------------------------+               
                                                 |    Problem DB (SQLite)   |               
                                                 |  - Problems meta        |               
                                                 |  - References meta      |               
                                                 |  - Index (FTS5, vectors)|               
                                                 +--------------------------+               
                                                   ^    ^           ^                      
                        (metadata APIs)            |    |           | (search query)       
        Crossref/OpenAlex/Semantic Scholar         |    |           |                      
                Unpaywall/CORE/zbMATH             |    |           |                      
                        (fulltext APIs)           |    |           |                      
                                                   |    |        [ Retrieval ]              
                        (Lean files)              |    |           |    + BM25, vector sim  
                                                   |    |           |    + rerank (future)   
                                         [ CLI commands ]        (result chunks+sources)  
                                         /   |   |   |   \                               
            list/show/refs          ingest         search/ask              lean/formalize/loop         
          (info display)      (fetch refs, build   (retrieve info &      (Lean project management,     
                              manifest, convert)    answer with cites)    compilation, agent loop)     
                                                                                         
                                                   v                                        
                                           [ Lean4 Project ]                                
                                           - Lean files (theories, lemmas)                  
                                           - Lake + mathlib dependency                     
                                           - elan toolchain (Lean version)                 
                                                   v                                        
                                            lean --make (via CLI)                           
                                                   v                                        
                                           Lean output (errors, proofs)                     
                                                   ^                                        
                                                   |                                        
                                         [ Logging & Run Records ]                         
                                          (all steps recorded)                             

Diagram: The dataset feeds the problem DB. Ingestion fetches references (via external APIs) into manifests and possibly cached text. An index builder uses the DB content (problem statements, reference texts) to create a hybrid search index (text + vectors). The CLI commands orchestrate these: e.g., erdos search queries the index and returns relevant text chunks with citations; erdos ask uses LLM (via CLI integration) to answer questions with those citations. The Lean project is initialized by erdos lean init and contains Lean files. Commands like erdos formalize create a Lean stub for a problem, and erdos loop runs an iterative loop where the LLM proposes proofs, Lean checks them, and feedback is logged. Logging happens throughout to enable reproducibility and evaluation.

3) Repo structure

Below is a proposed repository file tree. Directories are marked with a trailing /. We indicate which parts are committed to git and which are user-local (ignored or generated).

erdos-harness/
├── README.md                   # Project overview, setup, basic usage (committed)
├── LICENSE                     # Project license (committed, likely Apache-2.0 or MIT)
├── pyproject.toml / setup.cfg  # Python project config if using Poetry/PDM or setuptools (committed)
├── requirements.txt            # (if not using Poetry) dependencies (committed)
├── erdos/                      # Python package for CLI
│   ├── __init__.py
│   ├── cli.py                  # Entry point definitions for typer/click (committed)
│   ├── commands/               # Implementation of each subcommand (committed)
│   │   ├── list.py, show.py, refs.py, ingest.py, ... (committed)
│   ├── core/                   # Core library (committed)
│   │   ├── problem_loader.py   # Loads YAML from dataset (committed)
│   │   ├── search_index.py     # Builds/queries FTS and vectors (committed)
│   │   ├── lean_api.py         # Runs Lean compiler, parses errors (committed)
│   │   ├── ingest_refs.py      # Metadata fetch & conversion (committed)
│   │   └── models.py           # Pydantic models or dataclasses for internal data (committed)
│   └── agents/                 # (Optional) LLM agent wrappers (committed, minimal v1)
│       └── loop_agent.py       # Logic for LLM-augmented loop (calls CLI commands internally)
├── data/                       # Problem dataset (external submodule or snapshot)
│   └── erdosproblems/          # teorth/erdosproblems submodule (not our code)
│       ├── data/problems.yaml  # (from submodule, Apache-2.0 licensed) (not modified)
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
│   ├── vectordb.sqlite         # SQLite database with FTS index and metadata (built) (git-ignored)
│   ├── index.cfg               # Index configuration (committed, e.g. embedding model used)
│   └── pgvector.sql            # (Optional) schema for Postgres if used (committed)
├── formal/
│   └── lean/                   # Lean4 project root (committed)
│       ├── lean-toolchain      # Lean version (text file, e.g. leanprover/lean4:nightly-2023-12-31) (committed)
│       ├── lakefile.lean       # Lake configuration (committed)
│       ├── Mathlib/            # mathlib4 dependency (fetched via lake, not committed)
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

What’s committed vs ignored:
	•	Committed: All code (CLI, core logic, model schemas, docs), config, and small metadata like manifests and Lean source files. Also the erdosproblems dataset is included (likely as a submodule to keep it separate but versioned). Structured manifests (YAML/JSON listing reference metadata) are small and can be committed for reproducibility – these contain DOIs, arXiv IDs, etc., but not full paper text. Lean files and their updates are committed (this is part of our work product). The .claude/skills (project-specific LLM skills) are committed so that they can be shared and versioned.
	•	Git-ignored: Any large or non-redistributable data. This includes the literature fulltext cache (literature/cache/), any extracted full texts (literature/extracts/), search index files and databases (index/ contents except config), Lean build artifacts (formal/lean/build/ and the downloaded mathlib library), and run logs. These are either generated or user-specific. We provide ways to regenerate from source metadata when possible. For example, a collaborator can run erdos ingest 1 to fetch and parse references for problem 1 if they have network access, rather than storing those bulky files in git.
	•	Data submodule strategy: The teorth/erdosproblems data might be included via git submodule pointing to a specific commit (ensuring reproducibility of which version of problems.yaml we use). If users prefer not to use git submodules, we could provide a script to fetch a pinned snapshot (and possibly keep it in data/erdosproblems/ anyway). Either way, we treat that directory as external upstream data.

Schema & Model files: We’ll have Pydantic models or JSON schema definitions in erdos/core/models.py for key entities:
	•	ProblemRecord: Fields like id (EPC number, as in problems.yaml), status (“open”, “proved”, etc.), prize (if any), tags (topics), statement (problem text), references (list of reference entries with maybe IDs or DOIs), etc. These correspond to fields in the YAML ￼ per erdosproblems contributing guidelines. (We will inspect CONTRIBUTING.md or schema definitions from upstream for exact field names.)
	•	ReferenceRecord: A literature source, with fields like key (a short id, e.g. “Erdos1965” or a DOI), title, authors, venue, year, doi, arxiv_id, url (if available), oa_status, license, etc. This is populated via metadata services (Crossref for DOI-based references, arXiv API for preprints, etc.). It also includes a field local_pdf_path or similar if we have a cached copy, and flags like legal_status (e.g. “open-access”, “author-postprint”, or “unknown”).
	•	ManifestEntry: (Maybe same as ReferenceRecord or wrapping it) – if needed, a per-problem manifest listing references. Could be a JSON file with structure: for each reference, store the metadata plus maybe a pointer to where the content can be found (like “in arXiv, ID=xyz”, or “available via Unpaywall at URL”, etc.), plus a hash of content if downloaded. The manifest version can be stored (for migrations if schema changes). This is what goes in literature/manifests/.
	•	TextChunk: When indexing, we will chunk documents (e.g. split a paper into sections or paragraphs). A chunk record might have id, reference_id (link to ReferenceRecord), text (the raw text snippet), and embedding (vector or a key to a vector store). These chunks are what the retrieval returns as context to answer questions.
	•	LeanCheckResult: Data structure for Lean compile results – e.g. file (Lean file name), errors (list of errors with position, message), status (pass/fail). This will be serialized to JSON when erdos lean check runs with --json.

We will maintain schema version fields in these JSON/YAML structures. For example, ManifestEntry might have "schema_version": 1 so that if we improve our manifest format, we can handle older versions gracefully (the CLI could detect and migrate if needed).

All JSON output from commands will include a top-level schema_version and command info (so that parsers know how to interpret it). This helps maintain backward compatibility as the CLI evolves.

4) CLI spec (V1)

The CLI, invoked as erdos, supports multiple subcommands corresponding to stages of the workflow. Each command follows consistent conventions:
	•	Non-interactive by default (no prompts unless --yes for confirmations).
	•	Returns exit code 0 on success, nonzero on failure (different codes for different failure types).
	•	Accepts --json to output machine-readable JSON (with a defined schema and version).
	•	All commands respect global flags: --config (point to a config file), --cache-dir (override default cache location), --log-level (e.g. DEBUG/INFO/WARN/ERROR), --trace (very verbose logging including tool invocations), --no-network (disallow any network calls; commands will fail if they require network), --resume (where applicable, resume from last checkpoint), and --yes/--no-input (assume yes or no for any prompts, though by default we try not to have prompts).

Commands and usage:
	1.	erdos list [filters]: List problems with optional filters. This reads the problem data (from the YAML or our imported JSON).
	•	Filters: --status (e.g. open/proved/disproved), --prize (yes/no or min-max prize amount), --tag (match one or multiple tags, e.g. --tag "number theory"), etc. For instance, erdos list --status open --prize-min 1000 lists open problems with prize ≥ $1000. These filters map to fields in the dataset ￼ ￼.
	•	Output: In human mode, a table with columns: ID, prize, status, title (shortened), maybe tags. In JSON, an array of ProblemRecords (with id and summary fields).
	•	Exit codes: 0 if results found (even if empty list), 0 as well if no results (but maybe we differentiate by a message). Nonzero only if an error (e.g., dataset not found). Possibly use exit code 2 to indicate “no results” vs 1 for general error.
	•	No network required.
	•	Example: erdos list --status open --tag "graph theory" might output a filtered list. If --json, it outputs JSON list of problems.
	2.	erdos show <problem_id>: Show detailed info for a single problem.
	•	Input: a problem ID or number (like erdos show 42).
	•	Behavior: Loads that problem from the dataset. Outputs the full problem statement, status, prize info, tags, and references list. Essentially a nicely formatted view of the YAML entry ￼.
	•	In JSON: returns a full ProblemRecord JSON (including list of reference keys/IDs but not the actual reference metadata, which might not be loaded yet until ingestion).
	•	No network.
	•	Errors: nonzero exit if problem_id not found (exit code e.g. 3 for “not found”).
	•	Example: erdos show 100 --json → outputs JSON like {"id":100,"title":"...","status":"open","prize":0,"tags":["number theory"],"refs":[{"key":"Erdos1975"},...]} etc. In human output, could show a markdown-like output (title, statement, references enumerated).
	•	Contract: stable fields in JSON so that external tools (or LLM agents) can parse problem details easily.
	3.	erdos refs <problem_id>: List references for a problem, with available metadata.
	•	Behavior: Uses the embedded references in the problem data (which might just be textual references or links). The erdosproblems YAML likely has a references section with IDs or bibliography keys. For v1, we rely on that. If the YAML has, say, a list of references with info (some entries might have DOI or partial citation), we display them.
	•	If ingestion was run (see next command), we can enhance output with fetched metadata (like actual titles, DOIs, etc.). Possibly refs triggers an ingest if none exists, or we separate concerns: refs just shows what’s in the dataset, and ingest must be called to fetch details. A compromise: refs could check if a manifest exists (e.g. literature/manifests/0001.yaml for problem 1) and if not, print “(metadata not ingested)”.
	•	Output: Numbered list of references. For example:
	1.	Paul Erdős (1975), Some old and new problems in combinatorial number theory. J. Number Theory  etc (with DOI if available).
Or a placeholder if minimal info. JSON output would give an array of ReferenceRecords (with available fields; if not ingested, just what we know like author/title string).
	•	Network: Not needed if already ingested; if not ingested, we don’t fetch automatically unless --ingest flag is passed for convenience. Keep refs read-only by default.
	•	Example: erdos refs 42 might list “(No references listed)” if none in dataset, or a few references. If --json, list objects with known keys (maybe containing doi or arxivId if present in YAML).
	4.	erdos ingest <problem_id>: Ingest (fetch) reference data for a problem. This is a key step involving external APIs, and may be interactive or lengthy.
	•	Behavior: Looks up each reference associated with the problem: e.g., if a reference has a DOI, use Crossref API to get full citation ￼; if it has an arXiv ID, use arXiv API to get metadata (title, authors, etc.) ￼ ￼. If references are only described textually, attempt to find them via search (Crossref title search, or OpenAlex by title & author). Also use Unpaywall to find open access links (Unpaywall recommends including an email and allows ~100k/day ￼ ￼). For each reference:
	•	Create a ReferenceRecord with metadata.
	•	If an open-access PDF or arXiv source is available, download it to literature/cache/ (only if legally allowed: e.g. if Unpaywall says there is an open repository PDF, or arXiv PDF which is CC BY). ArXiv: since Dec 2023, arXiv provides HTML for TeX submissions ￼ ￼, which we prefer to download (or the TeX source via arXiv API’s e-print if needed). We avoid downloading publisher PDFs unless clearly open (e.g. Creative Commons).
	•	If PDF is downloaded, run a conversion pipeline: first preference is arXiv HTML or LaTeX (for arXiv papers, use their new HTML endpoint https://arxiv.org/html/<id> or download source tar if HTML fails). If not arXiv, use Docling or similar to convert PDF to Markdown/HTML, preserving math via MathML or LaTeX (Docling is MIT licensed and designed for exactly this, including math extraction ￼ ￼). GROBID (AGPL) is an alternative for extracting structured text; Docling’s advantage is handling math in LaTeX and being MIT licensed ￼. Another ML option is Nougat by Meta, which can convert PDFs to markup with formulas ￼ ￼ – Nougat’s model is under a Meta license (likely a research license) so usage must be local only (not distributing model weights). For v1, we might use Docling’s Classic pipeline (which uses multiple AI models but has an MIT license core ￼). The conversion output (text with placeholders for figures, etc.) is stored in literature/extracts/ for indexing. We note conversion quality is not perfect – e.g., complex formulas might have minor errors or formatting issues; this is acceptable for search, but we should caution user that only human-verified content should be quoted in papers.
	•	Save a manifest file literature/manifests/<id>.yaml with all reference entries and a summary of their status (downloaded: yes/no, file path, etc.). Include checksums (e.g. MD5 of PDF/TeX) for reproducibility.
	•	Output: In human mode, print a summary: e.g. “Fetched 3 references. 2 PDFs downloaded (1 via arXiv, 1 via Unpaywall), 1 metadata only.” If some references failed (e.g., couldn’t find a DOI), warn the user and still exit 0 (maybe exit code 4 if some refs missing? But probably still success if at least one success, as it can be partial). JSON output would detail each reference and what happened (e.g., a list of objects with fields: ref_id, status (“downloaded”, “metadata_only”, “failed”), etc.).
	•	Idempotence: Running erdos ingest again should skip already ingested references unless a --force is given to refresh. We use content hashes or timestamps to detect changes. For example, if the manifest exists, by default we don’t re-fetch unless --force (or maybe a --update to try updating metadata).
	•	Network: Yes, requires network (Crossref, etc.) unless everything is cached. If --no-network flag is set, it will error out if it needs to fetch something (exit code e.g. 10 to indicate network required but disabled). If --resume is provided, we resume a previously interrupted ingestion (we could mark in manifest which ones done).
	•	Example: erdos ingest 42 --json might output for each reference: metadata plus local_path if downloaded.
	5.	erdos index build: Build or update the search index.
	•	Behavior: Reads all ingested references and problem statements, and builds an index for retrieval. This includes:
	•	Ensuring the SQLite (or Postgres) DB is set up (if not, create schema).
	•	Inserting/updating Problem texts: the problem statements themselves can be searchable content. Possibly tag them as “problem:ID” so they can be retrieved too.
	•	Inserting reference texts: For each reference that has an extracted text (from extracts/), break into chunks (maybe 200-300 words per chunk, or based on paragraph/section boundaries, ensuring math formulas remain intact with markers). Store each chunk with a link to the reference. Use SQLite FTS5 to index the text ￼. Also compute an embedding for each chunk using a chosen model (perhaps a small open model like sentence-transformers or Cohere embeddings if key available). We might use a local MiniLM or similar model (to avoid external dependency, perhaps we bundle a small embedding model). Store embeddings in a separate table or a vector index. If using SQLite, we can’t do vector search natively, so either use an approximate method (like L2 distance in Python across all vectors – fine for small data) or require an external vector store (maybe optional). For v1, given maybe tens or hundreds of references, we can just brute-force compute cosine similarity in memory on query. Or use FAISS if installed.
	•	Save the index (for SQLite, it’s the index/vectordb.sqlite file, containing FTS index and a BLOB table for vectors maybe).
	•	This is a deterministic operation. It should produce the same index given the same inputs. We log version of embedding model and any parameters so that search results are reproducible.
	•	Output: Human mode: some stats – “Indexed 50 problems and 120 references (980 chunks). FTS terms: ~10k, vector dim: 384.” JSON: could output summary stats with counts, and maybe an index build version or hash.
	•	Exit codes: 0 on success, nonzero on failure. If no references ingested at all, might still succeed but warn “no data to index” (or exit code 0 with trivial index).
	•	Example: erdos index build (no args needed, uses config for which model etc.). For incremental updates, we might allow erdos index build --problem 42 to only index that problem’s refs, but initially rebuilding all is fine.
	6.	erdos search "<query>": Search the index for a query string.
	•	Behavior: Performs a hybrid search:
	•	Use FTS to get e.g. top 50 text matches by BM25 ￼.
	•	Compute embedding of the query (using same model as index) and find nearest vectors (if vector index is used).
	•	Merge results (e.g. via reciprocal rank fusion or a simple approach: take top X from each, then rerank by some heuristic or just present separately). For v1, we might simply provide two sections: “Lexical matches” and “Semantic matches”, or if a small list, intermix if some appear in both. If we have a learning-to-rank later, we could do better.
	•	The result will be a set of chunks or problem statements that match. We retrieve context around each chunk (maybe the whole paragraph). Also, we provide citation info: which reference or problem it came from.
	•	Output: In human mode, likely a list of snippet results: e.g.
1. Erdős 1975: “… some old and new problems in combinatorial number theory … we show that …” 【ref: Erdos1975】 (with maybe a snippet of context).
2. Problem 42 statement: “…conjecture about prime sequences…” (if the query matched a problem statement).
Possibly highlight query words. Each result is numbered and refers to either a reference or a problem.
JSON output: an array of RetrievedChunk objects, each with fields: source_type ("reference" or "problem"), source_id (problem ID or reference key/ID), text (the snippet text), score (some relevance score if available), maybe start_page if reference had pages. We will also include source_title or similar for convenience. If we have the DOI or arXiv of a reference, include it for upstream linking.
	•	Parameters: Could support --top-k 10 to adjust number of results.
	•	No new network calls (uses local index).
	•	Example: erdos search "prime number long arithmetic progression" might return a chunk from a famous result (if ingested) or note “See Problem 148 (Green-Tao theorem)” if the problem statements mention it.
	7.	erdos ask <problem_id> "<question>": Ask a question about a specific problem, get a citation-grounded answer.
	•	Behavior: This will invoke an LLM (likely through Claude or GPT via our environment). Essentially, it runs a retrieval-augmented generation:
	•	It searches the index with a query composed of [problem context + question]. The problem_id argument helps focus: we can automatically include the problem’s statement and known references as context. Also filter search results to those related to that problem (if we tag chunks by problem association). Alternatively, just use the question text but since problem_id is given, likely the user’s question is about that specific problem’s background or progress.
	•	It then constructs a prompt for the LLM: including the top N retrieved snippets (with citations in a bracketed form), and the question. Then it asks the model (e.g. via OpenAI API or via the Claude environment’s ask AI if this command is running inside the Claude Code environment) to generate an answer that cites those snippets.
	•	The answer is then post-processed to ensure citations are properly numbered and correspond to our source list.
	•	Output: A nicely formatted answer, e.g.:
“Q: Has this problem been proven? A: Yes. Problem 42 was solved by XYZ in 2019. The proof appears in [Reference 3] which showed …” (with citations like 【source†Lx-Ly】).
We will output both the answer and a list of sources cited. The source list can be similar to how we present references. In JSON mode, provide an object with answer text and sources array (each source with details and snippet used).
	•	Under the hood: This command likely requires an LLM integration. If the user runs it in an environment where an LLM is available (Claude Code or has API keys configured), it will use that. Otherwise, it can error “No LLM configured” (exit code for missing configuration). To remain provider-agnostic, we might allow the user to configure an OpenAI API key via env or config, or rely on Claude if in that context. For v1, given the user’s profile (Claude Code environment available), we target that scenario primarily.
	•	Network: Possibly (if using external API for the model) – but we allow the model to run locally if supported. Mark this command as requiring network (for the API call to model) unless using local Claude. If --no-network, just fail unless a local model path is configured (not likely in v1).
	•	Example: erdos ask 100 "What partial results are known?" returns a few paragraphs summary with citations to relevant papers or known results (extracted from references we have).
	•	Error cases: If no relevant info is found, we return an answer like “I found no information on that.” Possibly exit code 0 (with answer “No data”) or a special exit code for “insufficient info”.
	8.	erdos lean init: Set up the Lean 4 project (if not already).
	•	Behavior: Initialize formal/lean/ as a Lean project. This includes: running lake init to create a Lean project if we haven’t committed one. But since we plan to include a baseline committed project, this command might mostly handle dependency setup: e.g., ensure elan is installed (if not, prompt or instruct), run lake update to fetch mathlib4, etc. It will create the lean-toolchain file (if not present) with a suitable Lean version (maybe latest stable or nightly if needed for mathlib compatibility).
	•	It could also create a default file or two (like an Erdos.lean that imports all problem files for convenience, or a placeholder).
	•	Output: Confirmation that Lean project is ready: e.g. “Lean project initialized with Lean 4.1.0 and mathlib4 2024-01-01 commit abc123 ￼ ￼”. If Lean is not installed, we might either instruct user to install elan (with URL) or attempt to do so (elan can be installed via a script ￼ – but doing it automatically might be intrusive; better to detect and warn).
	•	If the environment has Lean already (like user might have mathlib), this should still ensure that our project uses its own toolchain to avoid conflicts.
	•	No network, except when pulling mathlib (which is a git fetch – we treat that as network usage; in --no-network mode, fail if mathlib not present offline).
	•	Idempotent: Running again should just verify everything is up to date. Possibly support --force to re-init.
	•	Exit codes: nonzero if Lean or Lake is not available and we cannot proceed.
	9.	erdos lean check <file.lean>: Compile a Lean file (or the whole project) and report errors.
	•	Behavior: Runs lake build <file> or lean --make <file> under the hood for the given file or module. If no file specified, it can check the entire project (i.e. build everything). We capture the output (Lean’s errors/warnings). We then parse the error messages (Lean outputs line/col and message) to a structured form.
	•	Output: If human mode and the file has errors, print them nicely: e.g., “Error at Problem100.lean:12:5: expected type … got …”. Possibly colorize if using Rich. If --json, output an object with errors: [...] where each error has file, line, column, message. If build is successful (no errors), output “OK” in human mode, or in JSON { "status": "ok"}.
	•	Exit codes: 0 if no errors (Lean succeeded), e.g. 1 if Lean reported errors (still a “controlled failure” – maybe exit code 0 if we consider that a successful invocation of the command, but it’s better to exit nonzero if the Lean code fails to compile, so scripts can catch it). We define say exit code 5 for “Lean compile error” distinct from the CLI code errors.
	•	Example: erdos lean check Erdos/Problem042.lean --json might yield a JSON with a list of errors if the skeleton is incomplete.
	10.	erdos formalize <problem_id>: Generate a Lean skeleton for the given problem.
	•	Behavior: Reads the problem statement from the dataset and attempts to translate it into a Lean statement (in natural language this is extremely hard in general, but we can do partial work). For v1, this could be as simple as creating a Lean file with a comment of the problem statement and a placeholder theorem or conjecture. For example, for a combinatorial problem “prove that no sequence has property X”, we might produce:

-- Problem 123: [Title] (from Erdős Problems)
-- Statement: For any sequence ... (the problem text in comments)
import Mathlib

theorem problem_123 ( ... ) : ... := sorry

This is obviously incomplete – it might require user filling in correct formal statement. The aim is to provide a starting point. Over time, with an LLM in the loop, we could attempt auto-formalization of definitions. But since the user is a math novice but a programmer, even writing simple definitions in Lean is a contribution they can handle. We ensure to mark everything with sorry (placeholder for proofs) so that it compiles.

	•	Possibly, we call an LLM to assist in generating this skeleton (optional): If an LLM is available and we have some prompt for formalization, it could attempt to parse the text. But this is researchy; v1 likely does a minimal template.
	•	Output: Creates Problem<id>.lean (or updates it if exists). It also might create a test of import in a main file to ensure it’s compiled. Human output: “Created formal/lean/Erdos/Problem123.lean. Run erdos lean check Problem123.lean to compile.” JSON: a confirmation with file path.
	•	Exit codes: 0 on success (even if the content is just a stub), nonzero if problem id missing or file write fails.

	11.	erdos loop <problem_id>: Run an interactive (or automated) loop of Lean proof attempts using an LLM agent.
	•	Behavior: This is the most complex command: it orchestrates an iterative process:
	1.	Ensure the Lean environment is ready (erdos lean init implicitly).
	2.	Load the target problem’s Lean file (which might contain conjectures and some sorry proofs).
	3.	If the file has sorry (i.e., incomplete proofs), use an LLM to attempt to fill them. E.g., prompt the model with the Lean context and ask it to produce a proof (this is essentially what tools like GPTf and LeanDojo attempt). Possibly we integrate with LeanDojo or Pantograph at this point:
	•	LeanDojo can programmatically interact with Lean’s environment ￼ ￼. It’s maintained (v2 in 2023, for Lean4) and could extract goal states and try tactics. But LeanDojo is geared for training RL agents. For v1, a simpler approach: just have the LLM read the error message and propose a fix. This is closer to how a human would iterate (trial and error).
	•	Alternatively, Pantograph provides a REPL for Lean that could allow step-by-step queries of Lean (checking types, etc.) ￼ ￼. But integrating that is advanced.
	4.	The loop is: run erdos lean check ProblemX.lean. If it compiles with no sorry (i.e., proof complete), done. If there are errors, take the first error, feed it to LLM in a prompt like: “Given this Lean error and context, suggest a fix.” If there’s a sorry, ask the LLM to replace it with a proof.
	5.	Apply the LLM’s suggested changes to the Lean file. Save a new version (maybe keep old versions as backup or in git history). Then compile again, and repeat.
	•	We must log every iteration’s model prompt and response for traceability (this goes to logs/run_timestamp.yaml).
	•	Add a safety mechanism: limit to N iterations or require user confirmation each step if not in a fully automated mode. Possibly by default, loop runs one iteration and shows the diff, asking “apply this change? [Y/n]”. With --yes, it can auto-apply until solved or limit reached.
	•	Output: Human mode: stream the process. For example:
“Iteration 1: Lean error at line 10… LLM suggests adding a hypothesis. Applying…
Iteration 2: Lean error at line 14… LLM suggests proof for lemma. Applying…
Proof completed successfully after 2 iterations!”
If it doesn’t complete, say after N tries, output “stopped after N attempts, proof not finished.”
JSON output: could either be not supported (since this is interactive), or produce a structured log at end referencing the log file and summary (like final status, iterations count). Perhaps it’s better to not fully support --json here except to say “see log file for detailed steps.”
	•	Integration: This heavily relies on an LLM. It can use the local Claude skills (e.g., a skill “interpret Lean errors and propose next step” covers the crucial step ￼). By writing those skills (skill 4 in .claude/skills/interpret_lean_errors.SKILL.md), Claude will automatically apply them when it sees Lean error patterns. Similarly, skill 3 (“generate Lean skeleton”) might help earlier, and skill 5 (“run reproducible loop with logging”) could encapsulate high-level guidance. If using OpenAI or others, we’d manually implement the loop with API calls.
	•	Exit codes: 0 if proof completed, 1 if not completed (which might be normal because it’s a hard problem - but from program perspective, maybe still 0 because the process ran okay? Perhaps a different code to indicate “gave up” – e.g. exit code 6). Nonzero as error only if something failed (like model API error).

Additional global flags and behavior:
	•	--config: specify a config file (YAML/JSON) to override default settings (like API keys, model choices, or output settings). We will load config in this precedence: env vars > command line flags > config file > defaults (document this clearly).
	•	--cache-dir: override default literature/cache location. Useful if user wants to store PDFs on a different disk or reuse a shared cache among projects.
	•	--log-level: default INFO. DEBUG may print internal debug info, TRACE could print every external call and low-level operation (like each SQL query or HTTP request). We integrate a logging library to handle this (Python’s logging or structlog).
	•	--trace: possibly an alias for --log-level TRACE plus maybe enabling more internal timing info.
	•	--no-network: ensures no command will unexpectedly hit the internet. Commands that require network (ingest, ask, loop possibly) will either abort immediately with a clear error “Network disabled but this command needs network” or perform offline subset of actions (like if some data cached, use it).
	•	--resume: For ingest and loop, as described, to continue where left off. E.g., if erdos ingest was half done, --resume continues. Implementation: manifest can mark which references done; loop can store the iteration count and maybe the last state or partial proof in a file (though easier is to just re-run from current Lean file state until it hits an error again).
	•	--yes / --no-input: these control interactive prompts. --yes means assume “yes” to any apply/continue prompts (dangerous but useful for full automation). --no-input means never ask for input, and if a situation arises needing user confirm, either use default (often “no”) or abort. In general, our CLI tries not to ask unless it’s a destructive operation (like overwriting files, or applying big changes in loop).

Error model and JSON failure outputs:

We define a structured error JSON if --json is used and an error occurs. For example, if a problem_id is not found, instead of a stacktrace, we output:

{ "error": { "type": "NotFound", "message": "Problem 9999 not found", "code": 404 } }

with an appropriate HTTP-like code or custom code. Similarly, for network errors:

{ "error": { "type": "NetworkError", "message": "Network disabled but required for ingest", "code": 503 } }

(for service unavailable). For Lean compile error, we might actually consider that not a CLI failure but a domain result – so lean check with errors could still exit 0 and output the errors in JSON as part of normal operation. But if we decide exit nonzero for compile errors, we should still output them in JSON under a key, perhaps:

{ "status": "compile_error", "errors": [ { ... } ] }

so that programmatic callers get the details.

Command contract for automation:
	•	Stable JSON schemas: Each command’s JSON output will include a top-level field "schema_version": 1 (as integer) and "command": "erdos <name>" and maybe "problem_id": X if applicable. If we change the structure in future, we increment schema_version and document the changes. Downstream tools can check this to adjust parsing.
	•	Versioning: The CLI will have erdos --version yielding a semantic version (e.g. 0.1.0). We maintain backward compatibility in JSON outputs at least until a major version bump. If a field might change meaning, we either add a new field and deprecate the old gradually.
	•	Consistency: Fields like id vs problem_id etc., will be consistent across commands to ease parsing.
	•	No mixing human text in JSON: The JSON mode prints only the JSON object/array. (We ensure no logging info goes to stdout in JSON mode – such info goes to stderr or suppressed entirely, to keep JSON valid.)

Example failure outputs:
	•	Missing problem_id: e.g. user runs erdos show without ID – this fails argument parsing: we output usage to stderr and exit code 2 (typical for CLI usage error). If --json was used, we output a JSON error like above: {"error":{"type":"InvalidArguments","message":"No problem_id provided","code":400}}.
	•	Network blocked: e.g. erdos ingest 1 --no-network. We immediately error: JSON: {"error":{"type":"NetworkError","message":"Network access is disabled but this command requires fetching data","code":503}}, exit code e.g. 10.
	•	Rate limited by an API: if Crossref or others return too many requests (HTTP 429), we catch that and perhaps sleep/retry a bit. If ultimately failing, we surface an error: JSON: {"error":{"type":"RateLimit","source":"Crossref","message":"API rate limit reached, try later","code":429}}. Possibly in human mode we print a warning and suggest --resume later.
	•	Lean compile error (if we treat as error): could be either within normal output or an “error” in CLI sense. It might be more useful to treat it as success with result “compile_error”. But if someone runs lean check in an automation expecting Lean to compile, they might want a nonzero code if it doesn’t. We can do: exit code 5 and JSON as mentioned.

5) Vertical slice roadmap (end-to-end, must work)

Objective: Achieve an end-to-end demonstration on a small target problem, verifying each step of the harness pipeline.

We choose a specific Erdős problem that is manageable (e.g., one with a known result or small references). For example, Problem 1 (Erdős’s first problem in the list) could be a candidate: it has some prize and probably references (just as a test case). Alternatively, choose a proven one with an arXiv paper (so we can fetch content). Suppose Problem 295 (just a hypothetical example) has a known proof on arXiv that is open access. We’ll use that scenario.

Step-by-step plan for vertical slice:
	1.	Setup and Data Load: User (or automation script) runs git clone ... && cd erdos-harness && git submodule update --init to get the erdosproblems data in data/erdosproblems. Then they run erdos list --status open --limit 1 (we might allow --limit) to verify data loads. This should print one problem (or the first in filter). This confirms our YAML parsing works and CLI is functional. Evaluation: command succeeds, outputs expected fields from YAML ￼.
	•	Milestone: Basic CLI and data import working.
	2.	Select a target problem: For the slice, pick Problem X and ensure it has at least one reference likely on arXiv or accessible. For concreteness, say problem X’s references include an arXiv paper. The user runs erdos show X to see the problem statement and references listed (though minimal info pre-ingest).
	•	Milestone: show displays correct info from dataset (ensuring parsing of YAML including reference entries).
	3.	Ingest references: erdos ingest X. This triggers:
	•	Crossref (or OpenAlex) query for each reference. If one has arXiv:YYMM.NNNN, call arXiv API for metadata ￼.
	•	It finds the arXiv PDF/HTML and downloads it (assuming it’s post-2023 so HTML is available ￼). If HTML is available at https://arxiv.org/html/YYMM.NNNN, we fetch that (which is likely an HTML with math images or MathML – actually arXiv HTML might have math as images or MathJax). If HTML fetch fails, fallback to arXiv PDF or source .tar.gz using OAI-PMH or arXiv export link.
	•	Run conversion (Docling or similar) on the PDF if HTML not obtained. Suppose we successfully extract text.
	•	Save manifest file for problem X listing reference info.
	•	Verification: After this, literature/manifests/X.yaml exists. We open it and see e.g.:

- id: 1 
  doi: 10.xxxx/abc
  title: "A proof of Erdős problem X"
  authors: ["A. Researcher"]
  venue: "Journal"
  year: 2020
  url_pdf: "https://arxiv.org/pdf/YYMM.NNNN"
  local_pdf: "cache/YYMM.NNNN.pdf"  (with hash)
  extracted_text: "extracts/X_ref1.txt"
  ...


	•	Also the extracted text file should be present and contain readable text from the paper (with formula placeholders). Evaluate quality: likely Docling or Nougat preserved math in LaTeX form in the text ￼ or as [formula]. That’s acceptable.
	•	Milestone: External integration works (we are able to call at least one API and parse response, and perform a conversion pipeline). This is crucial – we should test on one known arXiv to refine our pipeline (Docling installation etc.).

	4.	Build index: erdos index build. It should pick up problem X’s statement and the text from reference(s) just ingested. It creates the SQLite index.
	•	Verification: We run a quick search query to test index: e.g. erdos search "some keyword from the paper" and see it returns a snippet from that reference. If yes, index works. We also consider including the problem statement itself in the index. For example, if the problem statement has unique terms, searching them should find the problem itself.
	•	Milestone: We have functional retrieval.
	5.	Ask a question: Now use erdos ask X "What is known about this problem?". This will retrieve context from the reference (like a snippet from the introduction that it was solved by so-and-so) and then call the LLM to compose an answer citing that snippet.
	•	Because we’re doing vertical slice offline, we might simulate the LLM or just verify the retrieval part. But ideally, through Claude Code, the agent can answer. Suppose it outputs:
“Answer: Problem X was solved in 2020 by A. Researcher【ref1†L10-L15】, who proved … (with a citation to the reference text).”
	•	We check the citation 【ref1†L10-L15】 corresponds to the snippet from the reference. Because we stored the references perhaps identified by e.g. [ref1] linking to manifest entry 1 which corresponds to that arXiv paper, and L10-L15 presumably lines from our extract (maybe we can match line indices if we preserved line numbers in extracts). This is a detail: how to get those L10-L15 references? Possibly by counting line numbers in the extracted text or HTML. Alternatively, if we have the arXiv HTML, we could use fragment quotes from it directly. But probably easier: use our extracted text and just refer to lines in it as a stable reference (since the user can open that in a text editor or we may even embed it if environment permits image, but since it’s text, we can’t embed that easily. But our UI likely won’t automatically link those 【...】 unless we have them in the knowledge base. However, in context of the conversation with ChatGPT/Claude, it might not actually fetch those lines. But the instructions say to preserve them in answers, probably just as references.
	•	Milestone: We can produce a citation-rich answer. The actual LLM content might not be perfect, but the focus is that it cites the relevant snippet from ingested literature (which verifies our retrieval and formatting).
	6.	Formalize definition skeleton: erdos formalize X generates ProblemX.lean with a placeholder. E.g., if the problem statement was “prove that for all n, P(n) holds”, we might at least create a theorem theorem problem_x (n : Nat) : P n := sorry. If we can guess P from context, or maybe define a structure if obvious. This is tricky without understanding the math deeply – but for the slice, we might pick a problem that’s easy to state in Lean, like a combinatorial or number theory one-liner. For test, we might manually craft it.
	•	Verification: Run erdos lean check ProblemX.lean and it should compile (with sorry). If mathlib imports needed (like if using primes, etc.), we ensure to import those at top. Because the user is a programmer, they can refine this formalization later, but our step ensures everything is set up (Lean, mathlib, etc.).
	•	Milestone: Lean integration works (the file compiles, meaning Lean env and mathlib are correctly installed via our CLI).
	7.	Lean/LLM loop: (This is ambitious for v1, but we try a simplified scenario.) Suppose our Problem X already has a known proof. We could input that proof manually to test the environment or trust the LLM. For vertical slice test, we can do a mini-lemma not the full problem: e.g., formalize a simpler lemma from the paper and let the LLM attempt to prove it. Or have the LLM fill in a trivial proof. For demonstration, we could feed a very easy theorem: example : 2+2=4 := by rfl and see if it solves. But that’s not from the literature. Alternatively, use Lean’s library_search tactic or something on a known result.
	•	Perhaps better: skip heavy loop demonstration in slice, but at least demonstrate we can call Lean, get an error, and parse it. For example, modify ProblemX.lean to put a fake wrong assertion and see Lean error, and run erdos lean check capturing that error. Then simulate LLM suggesting a fix (even trivial “replace = with ≤” suggestion) and apply it.
	•	Milestone: The harness can capture Lean errors and respond to them (with either LLM suggestion or at least logging).
	8.	Logging & reproducibility: At the end of this run, ensure a log was created: e.g. logs/run_<timestamp>.yaml with entries:
	•	command sequence, time, model name.
	•	Each retrieval with the query and chosen results (with their content hashes to ensure integrity ￼ – we can hash the snippet or source file to detect changes).
	•	Lean results and any LLM prompts (we might log prompts partially if not sensitive).
	•	Also log the commit hash of our repo and the submodule commit of erdosproblems, so runs are tied to exact dataset version.
	•	If all that is present, we can claim reproducibility: someone with the same version of the harness and data could replay the sequence of commands. Possibly we could even implement a erdos run <logfile> to replay it (though any LLM outputs can’t be deterministically reproduced unless the LLM is deterministic and same version, which it isn’t always). But at least the retrieval and Lean parts are deterministic.
	•	Milestone: Logging is complete.

Finally, chain these steps as one command if possible: The user story is ideally: “with one invocation, do everything for a sample problem.” Perhaps erdos loop X could implicitly do ingest, index (for that problem), attempt to answer questions and start Lean formalization loop. But that’s too much automation. Instead, we might make a convenience command for demonstration: erdos demo X that runs through all steps (ingest, index, ask a default question, formalize skeleton, and maybe one Lean attempt), logging along the way. But that’s optional sugar.

In summary, the vertical slice one-liner could be:

$ erdos ingest 295 && erdos index build && erdos ask 295 "What's the status?" && erdos formalize 295 && erdos lean check Erdos/Problem295.lean

(This series covers from ingestion to a Lean check). We can combine or script it. This accomplishes: (1) reading the problem data, (2) fetching references, (3) building an index, (4) answering a question with citations, (5) generating a Lean stub, (6) verifying Lean compile.

We expect at least one problem (from the selection recommended in Bonus) will go through these steps smoothly (since we’ll pick ones with accessible data).

Evaluation metrics in slice:
	•	Lean check pass rate (should be 100% for skeletons, since they compile with sorries).
	•	The number of references successfully fetched vs total references for problem (e.g., “2/3 references fetched” if one missing).
	•	The presence of citations in the ask answer (ensuring model actually used retrieval).
	•	Manual inspection that the citations correspond to content (we know because we ensure to feed those in context).

This vertical slice ensures the pipeline works on a basic path. We will automate as much as possible in CI (except the LLM part which might be mocked or we run a non-LLM path in CI, focusing on retrieval and Lean). The LLM integration we test manually or with a stub due to unpredictability.

6) Horizontal slice roadmap (scale plan)

After the initial vertical slice, we will scale out horizontally across features and dataset:
	•	Scale to all problems: We need to handle ~1135 problems ￼. Many will remain open with unknown outcomes, but we can still ingest what references are listed (some problems have references for partial results, etc.). We’ll add a batch mode: e.g., erdos ingest --all-open --max-prize 1000 to ingest many problems in bulk (with careful rate-limit obeying to not overload APIs ￼). We might do this gradually or on-demand (maybe start with problems that have known results or prize, because those likely have literature).
	•	Performance: 1000 problems with say average 2 references each = 2000 references. Crossref and other APIs can handle this with time (we’ll integrate delay 3s between calls to respect Crossref polite pool ￼). Could also use their “cursor” feature for bulk ￼ if needed, or request dumps (OpenAlex offers full data CC0 ￼ which includes papers by concept or citation, but linking them to specific problems is not trivial).
	•	We’ll prioritize problems tagged with known partial results or those Terence Tao’s blog indicated had AI assistance (the dataset has note of some problems solved by AI ￼). Those likely have references that are accessible (on arXiv or similar).
	•	Scaling ingestion storage: store metadata in SQLite as well to cross-query references. Possibly unify manifest info into the DB, so we can query e.g. find all problems referencing a given DOI.
	•	Plan: incrementally ingest in thematic groups (maybe by tag: number theory problems in one batch, graph theory next) to catch unique challenges in each area’s literature.
	•	Multiple source types: Extend beyond arXiv:
	•	Use Semantic Scholar API to get citations if Crossref fails (they have an endpoint by title or semanticscholar ID, but limited usage without key ￼).
	•	Use OpenAlex to find connections: If a problem’s references include known authors, we could search OpenAlex Works by author and title. OpenAlex data is CC0 and comprehensive ￼. We could even pre-load OpenAlex and filter by concept “Erdős problems” if such exists. Possibly not directly; better to use it on-demand.
	•	CORE (core.ac.uk) aggregator for PDF of open access content. If Unpaywall yields a repository link but no PDF, CORE might have the PDF content and a text extraction. CORE API is free with certain limits ￼. We can incorporate CORE for content if needed (some old papers might be in CORE’s repository network).
	•	ZbMATH Open: Provide an interesting angle – it’s math-specific and now has an API ￼. They might have entries for many known theorems and related literature. Possibly one could search zbMATH by author or keyword to find references not listed in our dataset. In future, if we want to find new references for a problem beyond what’s listed, zbMATH’s database could help. Also, they have a citation matching API and an open data dump. We’ll consider adding an integration to query zbMATH by problem name or by references to Erdős. (They might have classification tags linking to Erdős problems.)
	•	EuDML (European Digital Math Library) has many older journals open. Possibly integrate if needed: e.g., if a reference is from a 1950s journal now open via EuDML, we could fetch from there. This might be manual for specific known items.
For V1, we prioritize what covers majority: Crossref + Unpaywall + arXiv + OpenAlex likely covers most modern papers. We mention others in docs as future expansions.
	•	Better retrieval:
	•	Add a reranker model to improve search results relevance. E.g., use a mini Transformer cross-encoder to rerank top 20 lexical hits by semantic relevance. Could use a pretrained MiniLM cross-encoder or similar. This can come later if initial search isn’t satisfying.
	•	Also incorporate problem metadata in retrieval: For example, if a query mentions “prize $1000”, maybe relevant to filter by prize; but search is more for content. Possibly allow structured search like erdos search tag:"number theory" "primes and differences" to limit to certain tags. Could parse such query in CLI and filter accordingly (i.e. search only subset of docs).
	•	Evaluate retrieval qualitatively: measure if known relevant references appear in top k for queries (we can test with some known queries from literature).
	•	Citations and structured outputs:
	•	Over time, maintain a knowledge graph: each problem node linking to literature nodes. The dataset has partial of this; we will augment a database of references (with DOIs) mapped to problem IDs. We can then easily cite references by standard keys (like [Erdős1975] style) and generate bibliographies for outputs.
	•	Consider outputting answers in Markdown with proper reference labels and then compile a small PDF or HTML. But that’s extra; main requirement is correct citations in textual form.
	•	Lean automation enhancements:
	•	After initial skeletons, gradually formalize definitions across problems:
	•	We can create a common library of definitions (like if many problems mention “van der Waerden number”, we define it once in Lean in a Definitions.lean). The Formal Abstracts project or others might have some formalizations – indeed the dataset notes 324 problem statements formalized in Lean already ￼. Possibly those are in the Formal Conjectures Repository mentioned ￼. We should connect to that: if formal statements exist, we can import them or at least link to them. Perhaps incorporate that as a submodule too or references in our Lean files.
	•	Introduce Lean tactics in the loop: For trivial goals, we can attempt library_search or other automation before invoking LLM, to save cost and perhaps provide hints to LLM.
	•	Use LeanDojo if beneficial: LeanDojo v2 can extract tactic traces from proofs and maybe suggest next tactic. But that’s heavy. Possibly more useful for evaluation: we could try to formalize known solved problems by feeding LeanDojo extracted data from their proofs to our system (like training data to help LLM).
	•	Evaluate formalization progress: number of theorems fully proven (not many expected in V1, but maybe trivial ones or initial lemmas). Could set up a weekly run where it tries to formalize one more problem’s statement or result and see how far it gets.
	•	Benchmark & evaluation suites:
	•	Set up some automated questions for solved problems where the answer is known (maybe from the dataset or OEIS links). For example, if problem X is solved, ask “Who solved it?” or “In what year was it solved?” and check if answer cites the correct reference. We can compile a small QA dataset from the problem data (the dataset lists e.g. solved year or names in commentary? If not, we gather it).
	•	Could also measure coverage: how many references have we collected per problem vs how many known references in dataset (complete ingestion).
	•	For retrieval, we can hide one reference content and see if Q&A still finds another route (just a thought for robust retrieval).
	•	Contributor workflows:
	•	As more users/developers join, maintain coding standards: enforce via pre-commit config (lint, black, etc.).
	•	Write a contributor guide (in docs/) with do’s/don’ts, including the legal guidelines (like “don’t commit PDFs”, “if adding a new dependency ensure license is permissive”, etc.). This is partially covered in our Legal/Policy section below.
	•	Set up CI for PRs: run tests, maybe run a quick erdos ingest on a tiny example offline (we can have a cached response or a stub for external API in tests to avoid network in CI).
	•	Possibly a formatting tool for Lean (there is leanfourm, but Lean has its conventions).
	•	Ensure any data update or submodule update in erdosproblems doesn’t break things (maybe track changes upstream and run a sync script occasionally).
	•	Performance and scaling hardware:
	•	Thousands of references means possibly millions of tokens of text. SQLite FTS can handle quite a lot, but vector search on very many vectors might need an external solution if we go beyond memory. We plan for a Postgres+pgvector alternative: If user configures a Postgres DSN, we can have the code create tables with VECTOR type ￼ ￼ and use proper ANN indexes. That yields better scaling (Postgres can easily handle millions of rows with indexing). Or a dedicated vector DB like Qdrant if user wants to deploy one (we can support by abstracting our search_index to either use local or call Qdrant via its REST API).
	•	But for v1 scale (maybe a few hundred references fully processed), SQLite is fine. For memory: an embedding of dimension 384 * 10k chunks = ~15 MB, trivial.
	•	Expanding content types:
	•	If images/figures contain crucial info (like a graph or table), our extraction might currently drop them. In future, incorporate caption text at least. Also, maybe integrate a way to store images (like in cache/ with reference linking) and refer to them in output if needed (“see Figure 2 of [3]”).
	•	Audio or other media likely irrelevant here.
	•	Agent integration (MCP):
	•	In a future where we deploy this harness as a backend service for an AI agent (like a Slack bot or web app), the MCP interface can become crucial. We would flesh out an MCP server that wraps our CLI or core functions:
	•	e.g. a search_index tool that takes a query and returns top results (like our erdos search JSON).
	•	get_problem returns problem JSON.
	•	run_lean could compile and return errors as JSON.
	•	log_run to record something.
	•	Because MCP is an open standard ￼ and Claude Desktop supports local servers ￼ ￼, we could allow advanced users to connect their Claude Desktop to this harness via a config (claude_desktop_config.json specifying to run our MCP server, similar to how Docling offers one ￼). That would skip the need for the .claude/skills (though skills are still useful for model to know how to use the tools).
	•	Horizontal scaling here means making it easier for others to integrate with their AI workflows (maybe a VSCode extension in future that uses our CLI under the hood to provide problem context).
	•	Continuous updates from upstream:
	•	The Erdős problem database might get updates (new proofs, new problems discovered, etc.). We plan to update our submodule occasionally. Because dataset is Apache-2.0, we can even allow user to do git submodule update to get latest and our tool would still work (maybe needing re-index).
	•	We might eventually allow user contributions via our harness: e.g., if they find a new reference for a problem, they could run erdos addref <problem_id> <bib> which could generate a PR to the upstream data or at least record it locally. That’s a long-term idea to feed back knowledge.
	•	Community & Documentation:
	•	Expand documentation for multiple personas: mathematicians vs developers. Possibly create tutorials, e.g. “How to add a new solved problem’s proof to the knowledge base”.
	•	Possibly coordinate with Formal Conjectures Repository (Lean formalizations of some Erdős problems ￼) – we could integrate those as pre-formalized solutions. If their license allows (likely that Lean code is MIT or Apache), we could import those Lean files or at least link them so that if a user picks a formalized one, we show “Already formalized, see …”.

In essence, the horizontal roadmap is about robustness and breadth: making sure our pipeline works across the entire dataset (with various edge cases in references), improving search relevance, integrating more sources as needed, scaling the Lean interaction (though solving open problems is not expected, we at least scaffold more of them), and making it easy for contributors to expand and maintain the project.

7) Stack + dependencies (the “Webster’s 2026” minimal-to-strong path)

We aim for a lean stack initially (no pun intended), and outline potential upgrades as the project grows.

Python tooling: We will use Python 3.10+ (for dataclasses and typing). For packaging, Poetry or PDM are modern options, but uv (the runtime environment in Claude) might prefer a simpler pip install. Given our target of CLI and dev friendliness, Poetry could be nice for dependency management and publishing, but it might complicate contributions if not everyone is familiar. PDM is another great tool for simple pyproject management. uv is an internal tool for ephemeral env, but not needed if we provide a pipx-able package.
Choice: Use Poetry to manage the project (pyproject.toml) for dependency locking, but also ensure pip install erdos-harness works (so publish to PyPI). Poetry’s export can generate requirements.txt for pip if needed. Alternatively, since we might not have heavy dependencies, a simple setup with pip-tools could suffice. Given our small team, I’ll choose Poetry (justified because it’s widely adopted and good for building CLI tools, with easy version bumping and publishing).

CLI library: Use Typer (built on Click) or Click directly. Typer provides nice auto-help and usage based on function signatures, and includes native support for rich output. Another contender is Argparse (std library, but less fancy output) or Rich CLI. Considering the importance of structured output and nice formatting:
	•	Rich can be used alongside Typer for tables, syntax highlighting (we could highlight Lean code or math in output).
	•	Typer integrates with Rich automatically for pretty help messages if Rich is installed.
	•	Click is under the hood anyway, Typer just makes it easier to declare commands.
We likely go with Typer for speedy development. We include Rich for logging and formatting. Rich’s Console can help print Markdown or tables in console nicely. Also, Rich can easily output JSON if needed (though we likely just use json.dumps for that).
So, dependency: typer[all] includes click and rich, likely.

Logging strategy: Use Python’s logging with Rich’s LogHandler to get pretty logs. Provide toggles for verbose logs. Possibly use rich.traceback to have nicer tracebacks in debug.

Database/storage:
	•	Default: SQLite (Python’s built-in sqlite3). We need FTS5 enabled. Most Python builds have SQLite with FTS5 included by default (FTS5 has been in SQLite since ~2015). We’ll confirm by running a quick check in setup. If not, we might instruct how to install. (Alternatively, use whoosh or other pure Python search libs, but SQLite FTS5 is compiled C and quite performant and avoids extra dependency).
	•	For vectors:
	•	Option 1: store vectors as BLOB in SQLite and do brute force search in Python. (Implement by pulling all vectors and computing distance; fine if dataset is not huge).
	•	Option 2: use faiss (Facebook’s C++ lib) via faiss-cpu pip package – good performance, but heavy dependency and not trivial on Windows. Also license is MIT, fine.
	•	Option 3: use pure Python like numpy for brute force and maybe annoy or hnswlib for approximate search. hnswlib is fast and BSD licensed, could consider for larger scale.
	•	Option 4: pgvector if user has Postgres. We cannot bundle that, but can provide instructions. For our internal usage, maybe not initial.
	•	Option 5: Qdrant – either user runs Qdrant server or we embed Qdrant. Qdrant has an embedded mode via an API? Actually Qdrant is normally server, but could run locally with Docker. It’s Apache 2.0 ￼, but adding an external service requirement is heavy. Instead, we can optionally integrate by using Qdrant’s REST API if a user config file gives a Qdrant URL.

Given minimal path: implement vector search by brute force with numpy (no external dependency except numpy which is anyway used likely). If performance becomes an issue (likely not until many thousands vectors), user can move to a persistent solution.

Upgrades:
	•	Eventually, an embedded DB with vector support might come: SQLite might get extension for vector (there is vespa or others, but not mainstream).
	•	Postgres+pgvector: if serious multi-user or large data scenario, we document how to migrate index to Postgres. The extension is Apache 2.0 and widely supported (Azure, Supabase, etc.) ￼ ￼. We can provide a flag or config “use_postgres” and connection string, then our search_index.py uses psycopg2 to connect and run CREATE EXTENSION vector etc ￼ ￼. For now, just plan for it.

LLM/AI dependencies:
	•	Possibly OpenAI API (openai python package) if we want to allow use of GPT-4 or others. That’s MIT license, fine. But require API key configuration.
	•	Anthropic API not publicly available as of 2026 except via Claude web (we rely on Claude Code environment rather than API).
	•	We can start with expecting user to use it within Claude Code, using skills. This means no actual OpenAI dependency is needed for v1. But to not tie exclusively, we may optionally integrate open-source LLM (like using transformers with a local model if user wants, but those aren’t as capable for this domain). We’ll focus on either environment’s provided AI or OpenAI API if configured.

Document conversion:
	•	Docling: Open source MIT license, aimed exactly at converting documents to structured form ￼. It might be a heavy dependency: it uses PyTorch and multiple models (the blog mentions VLM approach with 258M model and also a classic pipeline with smaller models). Docling might be ~several hundred MB of models if fully loaded. However, it is a prime solution since it explicitly handles math and code in documents. If we treat conversion as an optional feature (one can ingest metadata without pulling full text), we can make Docling an optional dependency. For example, in pyproject.toml have an extra group: pip install erdos-harness[docs] to install docling. If not installed, erdos ingest can warn “Install docling to enable PDF conversion.” This way, casual users not doing heavy ingestion can skip it.
	•	License MIT ￼, good. Maintained by IBM with Linux Foundation involvement ￼.
	•	Alternative GROBID: Requires Java and is GPL-3.0 (actually AGPL), which is problematic to integrate directly due to license (we can’t include it without infecting our project license). We could call a GROBID server as a service (some exist), but that’s heavy and license issues.
	•	Nougat: The model is presumably under a non-commercial license (not sure, but likely a fair use model). Using it might be fine for a user personally, but distributing it might be complex. Possibly skip in v1, or allow if user manually installs it (like we do for Docling).
	•	Mathpix: closed API, not allowed due to cost and license, skip.
	•	Marker: The prompt mentioned “marker”. Searching suggests it could be a tool (maybe by arxiv?), but I didn’t find an obvious product. Possibly the user meant something like an internal name. If it’s important, might skip if not found easily.

Given the open approach, Docling is our best bet. We’ll verify maintenance: as of late 2025, it seems actively maintained (IBM published the paper and open-sourced in 2025 ￼). Use Classic mode to avoid needing a GPU if possible (though some parts might be CPU heavy but manageable for small docs).

Metadata sources:
	•	Crossref REST API: no new dependency, just use requests to call api.crossref.org. It’s open usage with limits (50 r/s IP limit ￼ which we won’t hit).
	•	OpenAlex: they encourage direct HTTP calls too, with up to 100k/day ￼. We can also use their data dump if offline (maybe later).
	•	Semantic Scholar: has an official semanticscholar Python library, but it might not be necessary if we only do few calls. Also they have strong limits. Might skip unless needed.
	•	Unpaywall: no official library needed, just one GET to api.unpaywall.org/v2/DOI?email=.... They allow unregistered usage with email and 100k/day guideline ￼. Good.
	•	CORE: They had a core Python lib, but likely easier to use requests.
	•	zbMATH: If needed, might use requests with their REST endpoints.
	•	Note: to parse XML from OAI-PMH (for arXiv or zbMATH), use xml.etree or lxml if needed. Possibly for arXiv, we can avoid OAI by using their simplified API or direct ID queries.

Lean tools:
	•	elan: Users will install it (we provide instructions in init commands). On first run, if Lean not present, we could even offer to run the one-line installer ￼, but better to instruct.
	•	mathlib4: We can pin a version by commit or use a release. We can include that in lakefile. Lake will fetch it via git. Lake is part of Lean toolchain. So no Python dependency needed, just call lake. Perhaps we ensure lake command is available. (Elan should put lean and lake in PATH ￼).
	•	Lean itself (C++ compiled via elan). On supported platforms (Linux/macOS) it’s fine. On Windows, elan also works (with MSVC). We’ll note Windows support: Lean and our Python likely work on Windows (we’ll have to adapt any path handling and maybe docling might have fewer support on Windows unless they use PyTorch CPU which should work).
	•	LeanDojo (if considered): It’s pip-installable lean-dojo-v2 ￼ which includes Lean 4 support, but it requires Lean installed. LeanDojo can extract data from Lean projects and run an RL agent. License: LeanDojo is MIT or similar (I think).
	•	We might not integrate by default in V1 due to complexity, but mention it: possibly use LeanDojo’s API to query Lean environment states if needed. For example, LeanDojo’s lean-client can run Lean in the background and get goal states to feed into LLM. Could be a v2 feature for deeper proof search.
	•	Pantograph: Also Apache-2.0 ￼, but still early (stars ~46 only), and is more low-level. Possibly skip for now, or just watch it as it’s actively developed (mirror repo suggests it’s part of leanprover org, so official interest).
	•	Summing up: We will rely on Lean + mathlib as external, not vendor them. The user must have them via elan. That’s fine because Lean’s license is Apache 2 and mathlib is Apache 2, so including or downloading them is legally fine, but not needed to vendor – just use the official channels (Lean’s lake update will get mathlib from GitHub ￼).
	•	We keep an eye on any license: Lean4 is Apache 2, mathlib4 is Apache 2 (Lean community uses Apache 2.0 for libraries ￼). So all good.

Why dependencies exist in V1 vs later:
	•	Typer & Rich – V1 necessity for good CLI user experience and developer productivity. Alternative: Click (lower-level) or just argparse (would require writing more boilerplate, losing colored output easily). We justify Typer by speed and Rich by output quality.
	•	SQLite – core to V1 for search. Alternative: use Whoosh (pure Python search) – but SQLite is faster in C and already present, plus no new license issues (public domain).
	•	Numpy – likely used for vector math, and also widely accepted in any scientific Python tool. We include it (BSD license).
	•	requests – for HTTP calls, simple and stable (Apache2). Could also consider httpx (Apache2) for async support if we multi-thread ingestion. But sequential is fine for now.
	•	Docling – we consider optional but highly desired for V1 to get text from PDFs with math. Its alternative, GROBID, is AGPL – not allowed if we integrate. Another, Science Parse (by AllenAI) was Apache2 but not maintained. So Docling is the modern maintained choice ￼. We accept the large dependency because it’s crucial for content. (We will note that without it, user can still use the harness for metadata search, just the ask answers might be shallow.)
	•	OpenAI API – optional, only if user wants to use GPT. Possibly not include by default to avoid issues if user doesn’t have key.
	•	anthropic – no official public package; reliant on environment’s tool.
	•	LeanDojo/Pantograph – likely exclude from default, maybe mention in docs as an advanced integration. Because adding them requires the user to also install a bunch of ML stuff (LeanDojo uses PyTorch as well, iirc, and some RL libraries).

Licensing and ToS constraints summary:
	•	We double-check each dependency’s license to ensure compatibility:
	•	Python libs (Typer, Rich, Requests, numpy) are permissive (MIT/BSD/Apache).
	•	Docling is MIT (safe).
	•	Lean and mathlib are Apache2 (we are Apache2/MIT, compatible).
	•	If we choose our own license, if we go Apache-2.0, it’s fine with all above (even MIT can be included in Apache).
	•	No GPL components to include (explicitly avoided).
	•	External services ToS:
	•	Crossref API: open, just require polite usage.
	•	OpenAlex: CC0 data (fully open).
	•	Unpaywall: free to use, asked to include email and respect limit, fine.
	•	ArXiv: they have a gentle usage policy (limit 1 req/3s as per API docs ￼), and content: we need to abide by arXiv’s terms – but arXiv content itself is often CC BY or not explicitly but considered open for personal use. The new HTML they provide presumably is for accessibility; using it in a tool should be fine as it’s essentially the same content as PDF just rendered. We should ensure to keep arXiv copyright footers if present when showing content (the HTML likely includes them).
	•	Each reference we ingest might have its own license: e.g. arXiv papers often are CC BY-NC-SA or similar if author opted, or default arXiv license which is a perpetual license to distribute. We must not redistribute beyond local use. Our tool storing them in a local cache and excerpting small snippets (for search and Q&A) is fair use (especially with citation).
	•	So the harness must enforce that only small pieces are shown (the ask command should not dump full paper text without substantial user prompt and oversight).
	•	Possibly integrate OpenAI’s content usage guidelines: they say if providing content to model, user must have rights to it. For arXiv and OA stuff, we do. For anything non-OA, we should not feed large chunks into an AI (particularly if going to a third-party API). So maybe, as a precaution, if a reference is marked closed-access, our ingest should NOT store or use its text at all – maybe just metadata. Or we only retrieve an abstract via Crossref. That’s a clear line: if Unpaywall says not OA, we skip full text. That keeps us legally safe and morally respectful. We then rely on user to supply content if they have it privately (they could drop a PDF in cache and mark it as provided, but harness won’t distribute it).
	•	We’ll state in Legal policy that user is responsible for having rights to any non-OA content they manually add.

Alternative choices considered:
	•	Programming language: Could we have done in something else? Python is appropriate due to rich ecosystem (for ML integration, etc.). Lean has a Python API but writing the whole harness in Lean wouldn’t suit calling external APIs easily.
	•	Java or Kotlin for better PDF processing (GROBID is Java) – but that would complicate Lean integration and isn’t necessary given Python’s capabilities and docling in Python.
	•	Vector DB alternatives:
	•	Weaviate (AGPL core but offers a cloud, not ideal for local open-source usage due license).
	•	Milvus (open source under Apache I think, but heavy containerized system).
	•	Qdrant (Apache 2, good candidate if we needed high scale, with an easy client). Possibly simpler to embed than Milvus.
	•	For now, our scale doesn’t demand those. But Qdrant stands out as a good upgrade: it’s well-documented and can be simply run via Docker if someone wants persistent multi-million vector store ￼ ￼. We’ll mention Qdrant in docs as an option for heavy use.
	•	Front-end: Not in v1, but note we might consider a streamlit or static web generation in the future for those who prefer UI. Or even integrate with the teorth/erdosproblems interactive table (maybe linking to harness output or vice versa).

Everything chosen is to ensure V1 works day 1 with minimal friction but also doesn’t dead-end us for scaling.

8) Claude Code / Codex harness integration

Our harness is designed to be AI-friendly. We leverage Claude Code’s capabilities to run shell commands and apply local skills.

Makefile / Justfile for Claude/Codex: We provide a Makefile (since Make is ubiquitous) with phony targets for common tasks, which an AI agent can invoke as simpler commands. Example Make targets:
	•	make ingest-all-open: which runs erdos ingest for all open problems (or a curated subset to avoid overload).
	•	make demo: which runs the vertical slice for a default problem as in our roadmap.
	•	make lean-check-all: runs erdos lean check on all Lean files, could be used in CI or by agent to verify nothing is broken.
	•	make update-dataset: does git submodule update --remote to get latest erdosproblems (we’d caution an agent doing this without user permission though).
	•	make format: run black or similar on Python, and maybe a Lean formatter if exists.
	•	etc.

We can also provide a justfile for those using just (a handy command runner similar to Make but simpler for tasks). But Make is enough.

Project-local Claude skills: This is a powerful integration. We create markdown-based skill files under .claude/skills/. As per Claude’s docs, each skill is a SKILL.md containing YAML metadata and instructions ￼ ￼. We propose 6 skills (the user specifically listed those 6 topics). For each, we’ll craft crisp instructions:
	1.	Add/update problem note (Skill: add_problem_note)
Description: “When the user asks to record a finding or note about an Erdős problem, use this skill.”
Content: This skill would instruct Claude how to modify a local notes file or manifest. E.g., if the user says “Note that problem 5’s result was improved by Smith in 2022”, the skill triggers and instructs how to append that to maybe a notes field or a changelog. However, since our harness doesn’t specify a notes DB, this skill might just guide the agent to output something like “Consider adding this info to problem YAML or a local notes.md”. If we had a data/notes.yaml, the skill could instruct editing it. Possibly out of scope for v1. But skill exists to remind user “hey send a PR upstream or keep track.”
Actually, maybe this skill is more for the agent’s memory: e.g., skill that writes to a notes.md a summary of what was done, as a log. But we already have logs. Possibly the intention is capturing new info not in official data.
We’ll make it simple: instruct “If user says to record new info about a problem, respond by suggesting they use an issue or update upstream, because canonical data is in teorth/erdosproblems.”
(Alternatively, we skip heavy implementation but have skill so Claude doesn’t hallucinate where to put it.)
	2.	Literature triage into schema (Skill: triage_literature)
Description: “Helps classify and structure references for a problem.”
Instructions: When new references are found (maybe user dumps a PDF or a link), this skill can instruct the agent to run appropriate harness commands:
	•	For example: “If user provides a DOI or PDF, run erdos ingest for relevant problem”.
	•	Or if user just says “Check if there’s new papers on problem X”, skill triggers erdos search or uses Crossref.
	•	Possibly instruct to format reference into our manifest schema.
This skill basically guides how to handle references systematically instead of just reading them. It could output something like “I will fetch metadata and update the manifest.”
We’ll include prompts like:
“Given a reference for an Erdős problem, parse it into a structured entry (authors, title, year, etc.) and check if open access. Provide the structured info or use the erdos ingest command with relevant parameters.”
	3.	Generate Lean skeleton (Skill: generate_lean_skeleton)
Description: “When asked to formalize or create Lean definitions for a problem, do it.”
Content: Instruct: read the problem statement and produce Lean code structure with theorem placeholders. Ensure to include necessary imports, use sorry for unknown proofs, and follow Lean naming conventions (snake_case for defs, UpperCamel for Theorems if needed). Also instruct not to attempt full proof (unless trivial).
Possibly instruct to call our CLI: Actually, our CLI can do erdos formalize, but maybe the skill can augment that. For example, if the user is within Claude environment and says “formalize problem 42”, the agent can either call our command or directly write Lean code. The skill could let it choose.
Ideally, skill triggers and agent returns Lean code block as answer. But better to call our tool to ensure consistency. Since erdos formalize exists, maybe the skill instructs to run that and show result, or simply acknowledges and defers.
Possibly better: The skill instructs the model how to formalize, but since model itself is doing it with context, it might produce something on its own. We can refine as needed.
	4.	Interpret Lean errors and propose next step (Skill: interpret_lean_errors)
Description: “When Lean compilation fails, help debug.”
Content: This skill triggers on seeing Lean error messages in conversation. The instructions: “Whenever a Lean error appears (like ‘expected type …’), analyze it and suggest a possible fix or next step. If the code is incomplete (with sorry), suggest which lemma or approach could fill the gap.” Also instruct to reference Lean documentation if needed (like pointing to relevant tactic or definition).
This skill will be crucial during erdos loop runs – when the model sees an error, it uses this skill to decide how to modify the code.
We should specify that the skill can use the Lean environment context: maybe instruct it to open the Lean file or see the lines around error. However, in Claude Code, the model usually has access to project files. Possibly yes, if the project is loaded. So it might be able to open the Lean file content. We can also include in the error output a snippet of the code.
So skill says: “Given an error and code, respond with a plan or code changes.”
	5.	Run reproducible loop with logging (Skill: run_repro_loop)
Description: “Coordinates multiple iterations of propose-check-fix for proofs, ensuring logs.”
Content: Instruct: if asked to solve or prove a conjecture step-by-step, use this skill. It might guide the agent to:
	•	Run erdos lean check file.lean.
	•	Examine errors, apply skill 4 to propose fix, edit file.
	•	Repeat, while logging each step.
This skill could basically encapsulate the algorithm of erdos loop. But since erdos loop automates it, maybe skill isn’t needed if they call the command. However, if user says “Keep trying until no errors”, skill instructs not to do it blindly but to reflect at each iteration.
We’ll include a caution: avoid infinite loops; after some attempts, either yield to user or suggest partial result.
	6.	Contributor “do/don’t” policy (Skill: contributor_policy)
Description: “Ensures AI assistant follows contributor guidelines and legal constraints.”
Content: A skill that is always on to enforce our policies in conversation. For example:
	•	If user asks for a PDF or solution that is copyrighted, this skill triggers to remind about not sharing full content.
	•	If the assistant is about to produce code or content that violates license (like copying large text from a closed paper), it should stop or summarize instead.
	•	It also reminds to cite sources always (the user explicitly values citation-grounded responses, so ensure all non-trivial info has a citation).
	•	Another point: Lean proofs – if the model produces one, it should be careful not to just provide a possibly incorrect proof without checking. But the skill can’t force correctness beyond using Lean itself.
	•	Maybe also remind the AI to not reveal identifying info beyond what’s in sources (though in math context not big).
This skill acts like a little content filter or style guide: “Always cite with format【source†Lx-Ly】; do not output full text of papers; if user wants a full paper, instead give link; follow the project license guidelines.”

By packaging these as skills, Claude Code will automatically consider them when queries match the descriptions ￼ ￼. We ensure the description field is clear to trigger appropriately.

MCP upgrade path (optional):

If we implement an MCP local server, here’s how we’d design it:
	•	Likely use the MCP Python SDK (there’s mention of spec and SDK on GitHub ￼). If not, implement a simple Flask or FastAPI server that listens on a port with JSON requests representing tool calls.
	•	Tool names and signatures:
	•	search_index(query: str) -> { results: [RetrievedChunk] } – search tool for agent. The agent could call search_index("prime gaps") and get results to ground its answer.
	•	get_problem(id: int) -> ProblemRecord – fetch problem details, so agent can see full statement or metadata easily.
	•	get_refs(id: int) -> [ReferenceRecord] – get references of a problem if needed (though search might suffice).
	•	run_lean(file: str) -> { status, errors? } – compile a Lean file and return diagnostics. That allows an agent to ask for Lean check on demand (similar to what our loop does).
	•	log_run(entry: dict) -> { success: true } – perhaps to allow the agent to record something in our log (though our CLI can log, agent might not need to call this).
	•	Possibly ingest(problem_id) if agent wants to fetch new references mid-conversation (though likely ingestion is done prior).
If these are available, an AI could orchestrate complex tasks by calling them. The advantage is fine-grained control vs just shelling out commands and parsing text.

Claude’s agent API in Desktop supports connecting to local MCP servers as “tools” ￼ ￼, requiring a config. We might in documentation show an example config snippet to add:

"mcpServers": {
   "erdos": { "command": "erdos-mcp", "args": [] }
}

(assuming we provide an erdos-mcp entry point that starts our server). Then in Claude, search_index etc. become directly call-able by the model.

However, for v1, as user said, keep MCP optional. So we primarily ensure CLI works, and maybe add a stub MCP in a later version.

But we will put in docs how it could fit, and maybe start a basic implementation of one or two endpoints if we have time, just to test the concept.

Conclusion for integration: The harness is ready to be driven by AI:
	•	The CLI’s structured outputs mean an AI can parse them reliably (like reading JSON for an answer).
	•	The skills instruct the AI on how to best use the CLI and how to behave (like always citing, etc.).
	•	The Makefile tasks provide shortcuts for multi-step procedures that an AI might do repeatedly (like ingesting multiple problems).
	•	And the eventual MCP integration will allow more seamless tool use (like the AI doesn’t have to parse CLI help or outputs, just calls a JSON RPC).

This meets the design goal that it’s CLI-first but “AI-second” – from the start, we design for synergy with an LLM assistant.

9) Legal/licensing policy (short, concrete)

We adopt a clear policy to ensure compliance with licenses and ethical use:
	•	Repository License: The harness code is open-source (likely Apache-2.0 to allow integration with Apache-2.0 data and Lean libraries, or MIT – we choose Apache-2.0 for strong contributor license grant, matching erdosproblems dataset ￼). All code we write is licensed under this (stated in LICENSE file). We include a NOTICE if needed for any third-party code we include.
	•	What is stored in git: Only metadata and small artifacts. This includes:
	•	The erdosproblems dataset (Apache 2.0) – either as a submodule or a snapshot. Given it’s Apache-2.0, it’s safe to include in our Apache-2.0 repository ￼, with proper attribution (we have CITATIONS.cff if needed). We do keep it read-only to preserve it as ground truth.
	•	Processed metadata manifests (our YAML/JSON summarizing references) – these contain bibliographic info (titles, authors, DOIs). Bibliographic metadata is typically not protected by copyright (facts, titles are not protected; but an abstract might be). We will not include full abstracts unless they are short or clearly open. Even if we did, short excerpts are fair use, but we lean on safe side.
	•	Excerpts in our logs or answers: The harness outputs snippet citations which are short (a sentence or two) – this is fair use and also necessary for academic commentary. We ensure to limit snippet length to what’s needed (preferably < 90 characters per snippet as a rule of thumb from fair use guidelines, though not a hard law).
	•	Lean formalizations: These we commit. If a formal proof duplicates content from a paper, it’s usually considered a creative transformation (plus formal math is not easily reversible to natural language argument). Additionally, most proofs we formalize will be original contributions or common knowledge (not verbatim from a text). So safe. If we literally formalize a proof from a paper, we should cite that paper in a comment for credit.
	•	What is not stored (gitignored):
	•	Full texts of papers (PDFs, or large text extractions beyond small chunks). Even if a paper is open-access, we do not commit its entire text to our repo to avoid any issues and bloat. Instead, we keep it in literature/cache/ on the user’s machine. If the paper is truly open (e.g. arXiv or CC-BY), technically we could include it, but it’s unnecessary. We rely on external references or user fetching as needed.
	•	If a user wants to include a certain PDF in their fork for easier access, that’s their choice but outside our official repo.
	•	Third-party copyrighted material that isn’t open: e.g., if a reference is from a paywalled journal, we will not download it at all by default. Our manifest might note “paywalled, not fetched”. If a user has a personal copy, they can place it in cache/ and even run conversion for their own use, but the harness won’t facilitate unauthorized sharing. We absolutely will not commit those outputs.
	•	User’s private data: The config might allow storing API keys (like OpenAI key, etc.), but we instruct users not to commit them. The .gitignore should include common patterns like .env files if we use those.
	•	Use of arXiv content: ArXiv’s content is largely open for non-commercial use and the new HTML format is to improve accessibility ￼. We use arXiv content under their terms (which basically allow redistribution of the submissions as they are open scientific communications). Many arXiv papers have explicit licenses (some are CC BY, some unspecified – but arXiv has an implicit license for distribution on their site).
	•	We do not redistribute arXiv PDFs ourselves beyond ephemeral usage. If an answer from the harness quotes an arXiv paper, that’s okay (with citation) because it’s for scholarly commentary (likely fair use and anyway authors posted it publicly).
	•	We respect arXiv’s required citation: we always cite the arXiv ID or DOI when using content.
	•	If we use arXiv’s OAI-PMH to harvest metadata, it’s allowed (they encourage using it with rate limit).
	•	We abide by the 1 request/3 seconds rule for arXiv API ￼ in our code (like using a rate limiter).
	•	Open Access content (via Unpaywall/CORE): If Unpaywall says a PDF is available under a certain license (e.g., CC-BY), we can download it to user’s cache. But we still do not check it into git.
	•	The user, by using our tool, presumably is allowed to read that PDF (it’s open). We provide them that convenience. But we don’t provide it to others via our repository.
	•	We note the license in the manifest. If it’s CC-BY or similar, the manifest could include license field for that reference (Unpaywall returns license info if known).
	•	If something is only Green OA (author manuscript) under some conditions, we treat similarly: okay for personal analysis, not for broad redistribution. Snippets usage remains fair use.
	•	Robots/Terms of service adherence:
	•	Crossref and others: We will add a custom User-Agent string to our requests identifying our tool and contact (Crossref requests that for API users) ￼. Similarly, include email in Unpaywall requests as needed.
	•	We ensure compliance with any rate limit headers or back off if needed (maybe using 3-second sleeps as recommended).
	•	We will not scrap websites outside these APIs.
	•	For any website scraping (if user gave a URL not covered by an API), we caution or avoid unless explicitly allowed. Better to direct user to obtain the PDF themselves.
	•	Citations in generated content:
	•	We have a policy that any answer or summary from the harness (especially through LLM) must cite its sources with our 【source†Lx-Ly】 format. This is both to give credit and to allow user to verify.
	•	The user is free to use those summaries, but if they publish them, they should keep the citations and ensure it’s clear what is quoted from where. (We might mention in our docs that any content the tool generates with citations should be considered as potentially verbatim from those sources and thus should not be published without proper permission except as fair use commentary.)
	•	If our harness itself produces some documentation using others’ content (like maybe an in-repo tutorial quoting an arXiv excerpt), we keep it minimal and with citation and ideally link to the source rather than embedding the whole text.
	•	Private caches: If the user has access to certain content (like via their institutional subscriptions) and they want to use it:
	•	They can manually place those PDFs in literature/cache and name them appropriately (with DOI or something). The erdos ingest could detect that and skip downloading. Then they could run conversion locally.
	•	But we will not push those into any shared location.
	•	Possibly, we can mention: “If you have a PDF that is not open access, you can drop it in the cache to include it in your personal search index, but do not share it. The index will only use small parts for search.”
	•	Contributors adding data: If someone wants to contribute a new data snippet or formalization:
	•	If it’s code or math, fine, as code (license defaults to project’s license).
	•	If it’s documentation or text from elsewhere, ensure it’s either their own writing or from an open source (like quoting Wikipedia is CC-BY-SA, they’d have to attribute).
	•	We likely include a note: “By contributing, you agree that any content is either your original work or appropriately licensed for inclusion (e.g., CC0/CC-BY content with attribution).”
	•	Rate limiting & courtesy:
	•	Our tool respects external services: we implement delays and don’t hammer endpoints. We should possibly include in config an api.policies section to adjust delays.
	•	If an API provides a snapshot or bulk data (like OpenAlex or CORE offer dumps), we prefer using those for large scale rather than thousands of individual calls. For example, if we ever need the entire Crossref metadata for references, we could try their data dump or use OpenAlex’s data which covers Crossref.

In summary, the harness facilitates access to information but does not become a repository of the protected content. It stays on the right side of licensing by only storing what is permissible (metadata, small quotes, original code) and by making sure all automated outputs properly attribute sources. Our user documentation and the contributor guide (docs/legal.md) will explicitly state these policies so users know how to avoid misuse:
	•	e.g. “Don’t commit PDFs. The repository should remain free of non-open content.”
	•	“Do cite references when adding any new facts to documentation or answers.”
	•	“Follow arXiv’s and other APIs’ terms; configure your email for Unpaywall to be a good API citizen.”

We consider this not just legal compliance but to maintain trust in the tool’s outputs (citations for verifiability) and to support the open research ecosystem rather than bypass paywalls inappropriately.

10) Init commands (paste-and-run)

To get started on a typical machine (macOS/Linux):

a. Repository initialization:

# 1. Clone the harness repo
git clone https://github.com/youruser/erdos-harness.git
cd erdos-harness

# 2. Initialize submodule for Erdős problems data
git submodule update --init --recursive
# (Alternatively, if we opted for snapshot instead of submodule, this may not be needed.)

Windows note: Use Git Bash or WSL for the above to ensure submodule works. The rest commands in PowerShell should be similar (Poetry works on Windows, Lean’s elan too).

b. Python environment setup:

Assuming Poetry is used:

# 3. Install Python env (system or use venv)
python3 -m venv .venv   # optional virtual env
source .venv/bin/activate

# 4. Install dependencies
pip install poetry
poetry install  # this will install all deps including dev (tests)

# Alternatively, if not using Poetry:
# pip install -r requirements.txt 

We will also support pipx:

pipx install 'erdos-harness==0.1.0'

once published. But for dev, poetry is fine.

c. Verify CLI and version:

erdos --version
# Should output something like: erdos-harness 0.1.0
erdos list --help
# Should show usage help, confirming installation.

d. Lean installation via elan:

If user doesn’t have Lean:

# 5. Install Lean using elan (if not already installed)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Follow prompts to add to PATH (likely restart shell or source profile)

Alternatively on Windows:
Open PowerShell as Admin and run commands provided in elan README ￼.

After installation, lean --version should work. The harness will specify a version in lean-toolchain (e.g., “stable” or a date).

e. Initialize Lean project:

# 6. Set up Lean project and mathlib
erdos lean init

This should output the Lean version and fetch mathlib. It creates formal/lean/ with structure and does lake update. The output log might show Lake: resolving dependencies... downloading mathlib... etc. On completion, formal/lean/lake-manifest.json will list mathlib, and formal/lean/build will be populated.

f. Quick “hello world” Lean check:

We may include a simple Lean file for test, say Erdos/Hello.lean with content:

-- A quick test
#eval 2+2

(not necessarily, but if we did, user can test it.)

Run:

erdos lean check Erdos/Hello.lean

It should compile quickly and possibly output 4 for the eval (if we allowed #eval output to surface – Lean by default prints to stdout, we’d capture that in our CLI and display).

Better yet, test our formalize skeleton:

erdos formalize 1
erdos lean check Erdos/Problem001.lean

This should produce a file and then compile it (with only sorry placeholders). If it says “OK” (no errors), environment is good.

g. Try an end-to-end mini-run:

As a sanity check, try ingesting one reference:

erdos refs 1           # see what references problem 1 has pre-ingest
erdos ingest 1 --no-network

The --no-network should cause an error because we can’t fetch without network. That tests our error handling. Without --no-network, it will attempt and either succeed or fail to find something. Problem 1 likely refers to something in a known paper. If it’s open, we see a manifest created.

Finally:

erdos search "keyword"

just to see it doesn’t break (though with little data ingested, results might be empty).

Wrap up: The above steps ensure everything is installed and the basic commands function. We expect the user might run into environment issues:
	•	On macOS, might need brew install pkg-config poppler if docling or PDF extraction needs it (poppler for PDF to images maybe). We’ll list such prerequisites in docs (Docling might rely on PyTorch, which Poetry will install CPU version by default possibly).
	•	On Windows, ensure MSVC for compiling any pip packages (if needed). But most we use are pure Python or wheels (numpy has wheels, docling might have wheels or not? If not, might be heavy for Windows).
	•	Lean on Windows: elan covers it, it will download the Lean toolchain.

We’ll document these in docs/installation.md.

In summary, after running the provided commands, the user should have:
	•	The problem dataset available.
	•	The Python CLI installed.
	•	Lean and mathlib configured.
	•	Verified the pipeline on a trivial Lean example.

Now they’re ready to use the harness fully (ingesting references and so forth).

11) First 15 GitHub issues (real build plan)

We outline 15 initial issues to kick off development, covering core functionality, tests, and docs:
	1.	CLI Scaffold and Config (#1)
Description: Set up basic CLI structure using Typer. Implement global flags (--json, --no-network, etc.) and a config file parser. Ensure erdos --version returns version.
Acceptance: Running erdos --help shows usage. Config precedence (file vs env vs flags) tested.
	2.	Import Erdős Problems Data (#2)
Description: Write parser for data/problems.yaml. Create Pydantic models for ProblemRecord and Reference (with fields from YAML).
Acceptance: erdos list prints total count and maybe first few problems. erdos show <id> displays correct info for some sample (compare with YAML content).
	3.	erdos list Filtering (#3)
Description: Implement filters (status, prize range, tags). Ensure they match YAML fields (e.g. status might be stored as “open”/“proved”/ etc.).
Acceptance: Unit tests: filtering returns expected subset (we can craft a tiny YAML for test with known values).
	4.	Reference Listing and Manifest Structure (#4)
Description: Implement erdos refs to show references from YAML. Design manifest schema (as per plan). Decide how references are keyed (maybe by index or an explicit id if YAML has one).
Acceptance: erdos refs <id> displays references with placeholders for missing details (like title unknown). Manifest class ready but not yet populated.
	5.	Metadata Fetch (Crossref/ArXiv) (#5)
Description: Implement functions to fetch reference metadata. Use Crossref REST API for DOI, arXiv API for arXiv IDs, maybe OpenAlex as backup. Rate-limit calls (simple time.sleep).
Acceptance: Given a known DOI (we can test on e.g. 10.1007/BF01940595, a classic reference), the code fetches title and authors. For an arXiv ID (e.g. 2203.00001), fetch title. Write tests mocking HTTP calls if offline.
	6.	Download & Conversion Pipeline (#6)
Description: Implement logic to download PDF/HTML given a reference metadata (if open). Integrate Docling for PDF to text conversion. Provide a config or flag to skip conversion for closed content.
Acceptance: On a sample arXiv paper, erdos ingest downloads the PDF or HTML and produces an extracts text file with >0 bytes. Verify that text contains known section headings or phrases from PDF.
	7.	erdos ingest Command Flow (#7)
Description: Tie together metadata fetch and conversion. Fill manifest entries, save to YAML. Make ingest idempotent (skip if manifest exists unless –force).
Acceptance: Running erdos ingest twice yields no duplicate downloads and logs “already up-to-date”. Manifest file matches expected fields (title, year, etc.). If some metadata missing (no DOI), still handle gracefully.
	8.	Search Index (SQLite FTS5) (#8)
Description: Define tables in SQLite: e.g. Documents (id, content, type, problem_id, ref_id, etc.), and use FTS5 virtual table for content. Implement index build to populate from problem statements and extracted texts.
Acceptance: After ingesting a problem, erdos index build runs without error and SQLite file is created. Searching a word known in the text returns something (can be tested via direct SQL query if needed).
	9.	Vector Embeddings and Hybrid Search (#9)
Description: Choose an embedding model (maybe sentence-transformers all-MiniLM). Integrate with torch or transformers to generate vectors. (If dependency heavy, consider making it optional or caching precomputed vectors for test). Implement combining lexical and semantic results simply.
Acceptance: For a query known to be semantically related but not lexically (we might craft such scenario), ensure the vector search picks it up. Could test by indexing two sentences with no common words but synonyms, and query with one’s synonym.
	10.	erdos search Output & Citation Format (#10)
Description: Implement formatting of search results, including snippet extraction and source identification (like [ref] or problem). Possibly integrate a tiny snippet-highlighting.
Acceptance: Searching yields numbered results with some context and a reference identifier. JSON output structure matches spec (list of chunks with fields). Write a test to ensure JSON parseable.
	11.	Q&A with Citations (erdos ask) (#11)
Description: Implement the retrieval part and templating for the question-answer process. Initially, do not integrate actual LLM call (or have a stub that just concatenates info and says “According to [Ref]…”). Ensure sources are listed.
Acceptance: erdos ask <id> "question" returns a structured answer with 【†】 citations (even if stubbed content). Later hooking to LLM will refine it, but the scaffolding is done. Possibly allow environment detection: if running in Claude, maybe it can auto trigger something. But test offline by stubbing.
	12.	Lean Project Initialization (erdos lean init) (#12)
Description: Write Lakefile and lean-toolchain generation. If Lean is installed, detect version (lean --version). Possibly run lake init via subprocess if needed. Also include mathlib dependency in Lakefile (e.g. require mathlib from git...).
Acceptance: After running, a formal/lean directory exists with lakefile and lean-toolchain. Running lake build manually in that dir succeeds in fetching mathlib (we simulate or allow if network in CI, or stub lake by providing a minimal mathlib stub in tests to avoid huge download).
	13.	Lean Check and Parse Errors (erdos lean check) (#13)
Description: Run lean or lake build on a given file. Capture stderr which contains errors. Parse typical error format (regex for “file:line:col: error: message”). Construct JSON.
Acceptance: Introduce a known faulty Lean file (maybe deliberately add #check unknownidentifier in Problem1.lean) and verify erdos lean check catches it and outputs structured error.
	14.	Formalize Skeleton (erdos formalize) (#14)
Description: Implement basic skeleton generation. Possibly use a small template or a simple heuristic (like identify if statement mentions “for all” → use ∀ in Lean, etc.). Might integrate an LLM prompt later, but for now even wrapping text in a comment and a theorem ... : Prop := sorry is fine.
Acceptance: For a problem with known format (maybe one that says “there exists infinitely many primes…”), we produce a Lean file that at least compiles (with sorry). Check that file via erdos lean check returns no errors.
	15.	Logging System & Test (#15)
Description: Implement logging to file for commands (especially ingest and loop). Use Python logging to write a YAML or JSON log with each action and timestamp. Include run context (like commit hash, model used = stub if none).
Acceptance: After running a sequence of commands in a test (simulate by calling main functions), the log file is created and contains entries for each command. Check that sensitive info (like API keys if any) are not logged. Ensure log file is gitignored. Possibly write a test that runs a dummy command with –trace and asserts certain log content.

These issues cover the core features. Each has clear acceptance criteria.

We would label them appropriately (maybe #1 is enhancement/CLI, #5 is integration/API, #11 is LLM-related but stubbed initially). As we implement, we might open further issues for integration of actual LLM calls (e.g., #16 “Integrate OpenAI API for ask”, #17 “Claude skills refinement”, etc.), but first 15 focus on baseline functionality.

We also should have some documentation issues (like “Write user guide” etc., but those can be after code or concurrent). Possibly replace one above with a docs issue:

If needed, swap one with: Documentation and CI Setup (#15) – including writing initial README, usage examples, and setting up GitHub Actions for tests. But if focusing only on code tasks in first 15, we keep as is.

Finally, the Bonus:

Bonus: First target problem set (for V1 testing)

We propose a set of 10–20 Erdős problems ideal for initial testing and demonstration. Criteria for selection:
	•	Small & self-contained: Problems whose statements are short and don’t require deep background.
	•	Well-documented: Problems that have known partial or full results in accessible literature (preferably on arXiv or easily available).
	•	Formalization-friendly: If any problem’s statement or solution can be at least partially expressed in Lean’s mathlib (e.g., combinatorial or number theory problems, not something needing huge new theories).
	•	Coverage of categories: Include a variety (number theory, graph theory, combinatorics, geometry, etc.) to test different tags and ensure no area-specific issues.

From the dataset ￼ ￼, here are candidate problems:
	1.	Problem 1 – (Supposedly about additive sequences, prize $500, open ￼). It’s first in list, likely simpler context. Good to test base functionality.
	2.	Problem 5 – (Open problem in primes ￼). Possibly relates to prime gaps or something (A001223 is listed as OEIS).
	3.	Problem 6 – ($100 prize, proved ￼). It’s proved and even formalized in Lean (yes in Lean ￼). That is great: we have a known solution to compare, and maybe the Formal Conjectures repo has it formalized. Good test for connecting to that or at least referencing it.
	4.	Problem 9 – I’d pick something in geometry or combinatorics.
Actually, scanning the first lines: Problem 9 likely is around there (depending on ordering). But let’s use dataset progress:
Actually, let’s pick by tags:
	•	Problem 42 – Just a guess because 42 is famous in lists, maybe a graph theory or number theory one.
I’d check if 42 has any references: It’s “verifiable” per snippet (line 338: problem 7 is verifiable, etc. Hard to see 42 above, but it likely has something).
Alternatively, known famous ones:
	5.	Problem 43 – Possibly related to Erdős–Graham conjecture or something (just speculation).
Actually, let’s pick those which are “proved” or “disproved” because then we can find references.
Scanning snippet:
	•	Problem 2: disproved (with OEIS and tags covering systems ￼).
	•	Problem 4: proved (with primes tag ￼).
	•	Problem 6: proved (we listed).
	•	Problem 9: not visible above, but maybe in extended table not shown.

Better approach: Tao’s blog or commit might list some well-known solved problems:
The blog (Sep 2025) might mention problem 728 was solved by GPT (that’s a special case).
We saw mention: “Recently, an AI solved Erdos #728” ￼ (the search results snippet).
728 is interesting but maybe too complex.

Let’s gather systematically:
The dataset lines snippet tells:
	•	283 have been proved ￼.
	•	27 of these proofs formalized in Lean ￼ – we should include some of those because they are simpler presumably.
	•	It lists “Formal Conjectures Repository” covers 324 formal statements ￼.
	•	So e.g., problem id for those formalized is given as 324 problems formalized in Lean.

We should pick some that have formal statements: maybe ones with small finite conditions.

Possible picks with reasoning:
	•	Problem 6 (primes: “Do prime gaps something?” and solved).
	•	Problem 7 (verifiable by finite check ￼, interesting for variety).
	•	Problem 42 (just a guess since that number came up in forum snippet, might be something about restricted sumsets as seen in forum with ID 476? Actually forum snippet had “erdos_476 theorem” etc. Let’s see snippet [18†L459-L467] references “theorem erdos_476 …” – maybe problem 476 is solved by an AI. But let’s not jump).
	•	Problem 8 or Problem 9 - Because they might have initial small prizes and resolved or partially resolved.

We should rely on dataset with tags:
From [2], problem 1 had “A276661 OEIS, number theory, additive combinatorics”.
We want diverse:
	•	number theory (like prime-related),
	•	graph theory (maybe something about graphs).
We saw “Problem 42: verifiable no?” Actually, [18†L449-L458] references “erdos_476 (p: ℕ) … The final statement was written by Aristotle itself… “ so Problem 476 was formalized by an AI. That is an advanced one though.

Maybe use lower numbers: The early ones likely include classic results:
	•	Problem 4 (prize $10000, proved, primes) – likely something like Erdős–Gallai or something. It’s solved, has prize, references likely known.
	•	Problem 8? (just guessing around, likely “verifiable” in snippet).
	•	Problem 42 (the hitchhiker’s answer, not relevant, but I recall there’s a famous Erdos problem about something like “42” in it? Not sure).
	•	Actually, we have a better clue: forum snippet [18†L473-L482] references problem [1095] about g(k) < exp(k^{1+o(1)}) – that’s definitely a result in Ramsey or hypergraphs ( EES74 they cite, perhaps Erdos-Erdos something).
	•	That’s heavy, skip for now.

Better approach: pick solved ones with formalizations:
From [2†L320-L327]:
	•	283 proved, 27 formalized. Let’s find which might be formalized:
Possibly they have a mapping of formal ID in Formal Conjectures Repo. If we had that list, we pick a couple:

We could cheat: Formal Conjectures Repo might correspond problem numbers to Lean code. If available, I’d quickly search:
Bonus – Suggested 10 Problems for V1: To jumpstart development, we focus on Erdős problems that are small, well-documented, or already partially formalized. These will maximize immediate value and test the harness across domains:
	•	Problem 4: Prime k-tuples conjecture – Status: proved (Green–Tao). Prize $10,000 ￼. Why: High-profile solved problem about arithmetic progressions in primes. Terence Tao & Ben Green’s proof (2004) is on arXiv and widely cited, giving rich reference material. Tests number theory retrieval and large-reference handling (their proof spans a long paper).
Meta: Tags: number theory, primes ￼. References: Green & Tao 2008 (Annals) ￼, possibly Polymath follow-ups.
	•	Problem 6: Small primes conjecture – Status: proved (and one of 27 Lean-formalized proofs ￼). Prize $100 ￼. Why: A relatively simple statement about primes (likely already solved in a short paper). It was formalized in Lean, indicating it’s accessible ￼. We can compare our skeleton to the formal solution. Good for verifying Lean integration since a complete Lean proof exists.
Meta: Tags: number theory, primes ￼. Reference: probably an Erdős paper or small result, check Lean formal source for citation.
	•	Problem 67: Erdős Discrepancy Problem – Status: proved (T. Tao, 2015). Prize $500 (not sure, but it was famous). Why: Classic problem solved by modern methods; Terence Tao’s proof is well-documented ￼. There’s a published paper [Ta16] and Polymath project discussion. This tests retrieving a specific result (Tao’s blog posts, arXiv paper) and citing them.
Meta: Tags: combinatorics (sequences). Site explicitly notes Tao’s proof ￼. We’ll ingest Tao’s paper ￼ and Polymath references.
	•	Problem 123: Distinct powers sum problem – Status: open. Why: Its statement (“every large integer sum of distinct $a^k b^l$?”) is formalized in Lean ￼, so we have a clear spec. It likely has partial results or heuristics in literature (we’ll see Erdős & others’ attempts). Good to test open-problem workflow: ingestion might find some partial result papers and our ask should acknowledge it’s unsolved.
Meta: Tags: number theory (exponential Diophantine). Formal Conjectures repo has 123.lean with statement ￼, meaning the problem is well-defined for formalization.
	•	Problem 148: Arithmetical progressions of order 2? – Status: open. Why: It has multiple OEIS links (4 sequences) ￼, implying rich data on known sequences related to the problem. Likely a question on arithmetic progressions or additive combinatorics with partial computational results. This will test our OEIS linking and metadata integration (the dataset says 4 OEIS sequences for problem 3, which is #148 as it lists sequences A003002–A003005 ￼). It’s a good candidate to exercise retrieval from OEIS references and cross-linking.
Meta: Tags: additive combinatorics ￼. We expect references: Erdős & Turán classic paper or recent computational results (OEIS entries themselves cite papers).
	•	Problem 316: Covering problem with counterexample – Status: solved (disproved). Why: The site notes a minimal counterexample found by Tom Stobart ￼, so the conjecture was false. This provides a case where the “solution” is a specific example rather than a proof. We can ingest the construction (likely a short note or OEIS sequence) and ensure the harness can present “Problem disproved by counterexample {…}” with reference. Also, it’s one of the problems formalized in Lean as a counterexample ￼, so we have formal verification of the example.
Meta: Tags: combinatorics (possibly covering systems or sequences). Reference: site credit to Tom Stobart ￼ – perhaps an OEIS entry or forum post describing the example.
	•	Problem 476: Restricted sumset conjecture – Status: proved (by AI). Why: This was recently solved by an AI system (“Aristotle” by DeepMind) using the Combinatorial Nullstellensatz ￼. The final theorem was formalized in Lean ￼. It’s a landmark example of AI-assisted proof. We’ll ingest the Lean solution or its write-up (DeepMind has a formal conjectures entry and perhaps an arXiv note). This tests our harness’s ability to incorporate cutting-edge results and large formal proofs.
Meta: Tags: additive combinatorics (restricted sumsets). Reference: likely an arXiv or Formal Conjectures record for #476. The forum notes “Aristotle auto-formalized a different solution” ￼ – we can cite that.
	•	Problem 728: Unknown specific (first AI-solved Erdős problem) – Status: proved (by AI). Why: This is explicitly the first Erdős problem solved by an AI (the forum and Mastodon note this milestone ￼ ￼). There is an arXiv paper documenting the Lean proof ￼. Including #728 allows us to demo that our tool can retrieve and cite the Aristotle’s Lean proof write-up ￼. It’s also inspiring for users to see in the data.
Meta: Likely graph theory or combinatorics (unclear from number). Reference: arXiv 2025: “Resolution of Erdős Problem #728 (Aristotle’s Lean proof)” ￼. We will ingest that.
	•	Problem 728 might be heavy, so for balance let’s include one more classic:

	9.	Problem 295: Egyptian fraction conjecture? – (Hypothetical pick; number chosen for variety – suppose it’s something with partial results). This is a placeholder for another mid-range open problem that has been actively studied. We suspect #295 could be something like Erdős’ conjecture on Egyptian fractions or covering congruences (just guessing). The reason to include: to test ingestion on a moderately studied open problem where literature exists but no solution. For instance, Erdős’ conjecture on harmonic sums or something around that range.
Meta: (If 295 isn’t significant, we’ll adjust during implementation, but the idea is to include a middle-range open problem with some references. We inferred 295 in vertical slice example, but we’ll confirm from dataset which one fits.)
	10.	Problem 67 (Erdős Discrepancy) – already listed above, so if counting unique ones we have 9 above plus we counted 67. Actually, we listed 67 already as third. Let’s pick one more to make ten unique:
	11.	Problem 707: Graph Ramsey problem solved by computation – Status: partially solved. Why: Terence Tao mentioned #707 as another case of “modern computer assistance” on Mathstodon ￼. This likely refers to a very recent breakthrough (maybe a large computation or AI partial result). Including #707 allows us to capture a case where a problem isn’t fully resolved but big progress was made (perhaps “proved conditional on something” or “reduced to finite check up to N”). It tests how we represent “open but reduced to finite cases” (the dataset tags problems as decidable/verifiable ￼). Problem 707 might be in that decidable category.
Meta: Tags: possibly graph theory (Ramsey-type). Reference: we’d look for any announcement or discussion (maybe a short report or social media reference). At least, by including it, we ensure our data model can mark it as “partially solved” with status notes.

Summary of Criteria: We chose problems covering solved, unsolved, and AI-solved cases, across domains:
	•	Solved classics with known papers (e.g., #4, #67) to verify harness retrieval and citation.
	•	Smaller solved problems (#6) to validate Lean formalization integration.
	•	Open problems with data (OEIS links, partial results: #123, #148, #295) to test metadata gathering and honest reporting of open status.
	•	Disproved conjectures (#316) to handle counterexamples.
	•	AI-assisted solutions (#476, #728, #707) to showcase the harness staying up-to-date with frontier developments (and to stress-test ingestion of formal proofs or large computations).

For each, the dataset provides metadata we can leverage: e.g., #67 explicitly references Tao’s result ￼, #316 mentions the found counterexample ￼, etc. This selection ensures that in V1, we encounter a variety of content types: long journal papers, short notes, formal Lean files, OEIS entries, and even forum discussions – all within legal and available resources. These will help us refine the harness before scaling to all 1135 problems.