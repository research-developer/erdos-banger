# Master Qualifications & Build Decisions

> Companion document to `docs/specs/master-vision.md`. This captures scope decisions, risk mitigations, and concrete choices that guide the actual v1 implementation. The master vision remains the vision; this document is the pragmatic filter.

---

## 1) Scope Triage: What's Actually in V1

The master draft describes many capabilities. Here's what we're **actually building first**:

### V1.0 (Must Ship)

| Component | Scope | Notes |
|-----------|-------|-------|
| Dataset loading | Full | Parse enriched problems YAML, validate via Pydantic models |
| `erdos list` | Full | With filters (status, prize, tags) |
| `erdos show` | Full | Display single problem |
| `erdos refs` | Basic | Show refs from YAML only (no enrichment) |
| `erdos lean init` | Full | Set up Lean project, fetch mathlib |
| `erdos lean check` | Full | Compile file, parse errors to JSON |
| `erdos lean formalize` | Basic | Template-based skeleton generation |
| SQLite FTS | Basic | Problem statements only, no chunking |
| `erdos search` | Basic | BM25 only, no vectors |

### V1.1 (After Core Works)

| Component | Scope | Notes |
|-----------|-------|-------|
| `erdos ingest` | arXiv source + Crossref metadata | arXiv source tarball + extract; Crossref metadata for DOI; no PDF conversion |
| Reference enrichment | Crossref + arXiv API | Skip OpenAlex, Semantic Scholar, CORE for now |
| Full-text indexing | Deferred | v1 index/search uses problem statements/notes only; ingested extracts are stored for a future indexing spec |
| `erdos ask` | Basic RAG | Retrieval + LLM prompt, no reranking |

### V1.2+ (Deferred)

| Component | Why Deferred |
|-----------|--------------|
| Vector embeddings | BM25 is surprisingly good for technical text; adds complexity |
| PDF conversion (deferred to v2.0+) | Heavy dependency + edge case hell; use arXiv HTML/LaTeX in v1; optional `[pdf]` extra (Marker) is v2.0+ |
| MCP server | CLI + Claude skills sufficient for now |
| `erdos loop` automation | Need manual workflow validated first |
| Postgres/pgvector | SQLite handles our scale |
| Qdrant | Same as above |
| Multiple API fallbacks | One source working > many sources half-working |

**Decision:** We ship when `erdos show 6 && erdos lean init && erdos lean formalize 6 && erdos lean check` works end-to-end. That's the real v1.0 milestone.

---

## 2) True Vertical Slice (Day 1-3)

The master draft's "vertical slice" was actually horizontal. Here's the real vertical slice:

```bash
# This should work after 2-3 days of coding:
erdos show 6                           # Display problem 6 from YAML
erdos lean init                        # Set up Lean project with mathlib
erdos lean formalize 6                 # Generate Problem006.lean skeleton
erdos lean check Erdos/Problem006.lean # Verify it compiles with sorry
```

**No network. No APIs. No embeddings. No LLM.**

Just: can we read the data and produce a Lean file that compiles?

### Pre-Coding Manual Workflow

Before writing any code, manually execute this workflow for Problem 6:

1. [ ] Open `problems.yaml` from teorth/erdosproblems, find Problem 6
2. [ ] Note exact field names and structure (do they match our Pydantic models?)
3. [ ] Create a minimal `data/problems_enriched.yaml` entry for Problem 6 (title + statement + status)
4. [ ] Google its references, find the relevant arXiv paper
5. [ ] Read the paper, understand what the theorem actually states
6. [ ] Check if Problem 6 is in the Formal Conjectures Repository (verify current coverage at implementation time)
7. [ ] Write a Lean file by hand that states the theorem
8. [ ] Compile it against mathlib4, note what imports are needed
9. [ ] Document friction points encountered

**This manual pass will reveal problems the spec doesn't anticipate.**

---

## 3) Dependency Decisions (No More "Maybe")

The master draft has too many "possibly X or Y" statements. Here are hard decisions:

| Choice | Decision | Rationale |
|--------|----------|-----------|
| CLI framework | **Typer + Rich** | Not Click. Typer is faster to write, Rich output is nice |
| Package manager | **uv** | PEP 621 + `uv.lock`, fast, single toolchain |
| Database | **SQLite with FTS5** | Not Postgres. Not until we have 10k+ documents |
| Vector store | **None for v1** | BM25 only. Add vectors in v1.2 if retrieval quality demands it |
| Embedding model | **Skip for v1** | If we add later: SPECTER2 (scientific text) over MiniLM |
| PDF conversion | **Skip for v1** | arXiv HTML + LaTeX source only. `pdf` extra reserved for v2.0+ (Marker, see Spec 019) |
| Lean version | **leanprover/lean4:v4.12.0** | Pin exact version in `lean-toolchain` |
| mathlib4 | **Pin to tag matching Lean** | Use `mathlib4` tag matching `lean-toolchain` (e.g. `v4.12.0`) |
| LLM integration | **Claude Code environment** | Not OpenAI API for v1. Claude skills + shell commands |
| MCP | **Skip for v1** | CLI is sufficient |

---

## 4) PDF Conversion Strategy

PDF conversion is out of scope for v1. The `[pdf]` extra is reserved for v2.0+.

### Content Acquisition Strategy (Ordered by Priority)

1. **arXiv HTML** (post-Dec 2023 papers) - Clean, structured, math preserved
2. **arXiv source tarball** - LaTeX → text conversion is tractable
3. **Abstract only** (via OpenAlex/Crossref) - For non-arXiv papers
4. **Metadata only** - For paywalled content

If a paper isn't on arXiv and isn't open access, we record metadata and move on. We don't try to solve PDF extraction in v1.

### v2.0+ PDF Tooling Decision (Updated 2026-01-19)

**Selected:** Marker (GPL) - best quality for math PDF with LLM enhancement

**Rationale for GPL exception:**
- Marker is the only tool with both MIT-quality AND excellent math support
- Docling (MIT) is blocked by typer version conflict
- PyMuPDF (AGPL) has stricter copyleft requirements
- GPL is acceptable only as an opt-in extra; distributing builds that include it must comply with GPL obligations (core remains permissive)

**Install path:** `uv sync --extra pdf` will install Marker when Spec 019 is implemented.

See `docs/specs/spec-019-pdf-conversion.md` for full details.

---

## 5) Lean Formalization Strategy (Expanded)

The master draft is light on formalization details. This is the hardest part.

### Phase 1: Manual Template Development

Before automating anything:

1. **Pull Formal Conjectures Repository** - Many statements already formalized (verify current coverage at implementation time)
2. **Manually write 5 Problem*.lean files** for target problems (4, 6, 67, 123, 316)
3. **Document patterns:**
   - What mathlib imports are commonly needed?
   - How are number theory statements structured?
   - How are combinatorics statements structured?
   - What's the minimal compilable skeleton?

### Phase 2: Template-Based Generation

Use discovered patterns to build templates:

```lean
-- Template: Number Theory (prime-related)
import Mathlib.NumberTheory.Primes

/-- Problem {id}: {title}
{statement}
-/
theorem problem_{id} : {formal_statement} := by
  sorry
```

### Phase 3: LLM-Assisted (V1.2+)

Only after templates work:
- Feed problem statement + template to LLM
- LLM proposes `{formal_statement}` portion
- Human verifies it compiles and means what the problem says

**Key insight:** A skeleton that compiles but states the wrong theorem is worse than no skeleton. Correctness > automation.

---

## 6) GitHub Issues Breakdown

The master draft's 15 issues are too coarse. Here's a finer breakdown:

### Epic 1: Project Scaffolding (Issues 1-4)

1. **Repo structure and uv setup** - `pyproject.toml`, `uv.lock`, directory tree, `.gitignore`
2. **Typer CLI skeleton** - `erdos --version`, `--help`, global flags
3. **Config file parser** - YAML config loading, env var precedence
4. **Logging infrastructure** - Structured JSON logs to `logs/`

### Epic 2: Dataset Integration (Issues 5-8)

5. **Git submodule setup** - teorth/erdosproblems integration
6. **YAML parser for enriched problems** - Load v1 enriched YAML; detect upstream metadata-only format with a clear error
7. **Pydantic models** - ProblemRecord, ReferenceRecord
8. **`erdos list` command** - With filters, table output, JSON output

### Epic 3: Problem Display (Issues 9-10)

9. **`erdos show` command** - Full problem display
10. **`erdos refs` command** - Reference listing from YAML

### Epic 4: Lean Integration (Issues 11-15)

11. **Lean project structure** - lakefile.lean, lean-toolchain, directory setup
12. **`erdos lean init` command** - Detect elan, run lake update
13. **`erdos lean check` command** - Run lake build, capture stderr
14. **Lean error parser** - Regex for line:col:message format
15. **`erdos lean formalize` command** - Template-based skeleton generation

### Epic 5: Basic Search (Issues 16-18)

16. **SQLite schema** - Problems table, FTS5 virtual table
17. **Index builder** - Populate from problem statements
18. **`erdos search` command** - BM25 query, snippet extraction

### Epic 6: Ingestion (Issues 19-23) [V1.1]

19. **arXiv API client** - Metadata fetch by ID
20. **arXiv HTML fetcher** - Download ar5iv HTML
21. **arXiv source fetcher** - Download and extract tarball
22. **LaTeX to text converter** - Basic extraction, preserve math notation
23. **`erdos ingest` command** - Orchestrate fetch + convert + manifest

---

## 7) What Makes This Agent-Ready

Before handing to a coding agent, ensure:

### Hard Decisions Made
- [x] Typer, not Click
- [x] uv, not Poetry/PDM/pip-tools
- [x] SQLite, not Postgres
- [x] No vectors in v1
- [x] No PDF conversion in v1
- [x] Exact Lean version pinned

### Exact File Tree (V1.0)

```
erdos-banger/
├── README.md
├── LICENSE                          # Apache-2.0
├── pyproject.toml                   # PEP 621 project config
├── uv.lock                          # Locked deps (committed)
├── .python-version                  # Python pin for dev
├── src/
│   └── erdos/
│       ├── __init__.py
│       ├── cli.py                   # Typer app definition
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── list_cmd.py          # erdos list
│       │   ├── show.py              # erdos show
│       │   ├── refs.py              # erdos refs
│       │   ├── search.py            # erdos search
│       │   └── lean.py              # erdos lean init/check/formalize
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py            # Pydantic models
│       │   ├── problem_loader.py    # YAML parsing
│       │   ├── search_index.py      # SQLite FTS
│       │   └── lean_runner.py       # Subprocess lean/lake calls
│       ├── templates/
│       │   └── lean_skeleton.j2     # Jinja2 template for Lean files
│       └── py.typed                 # PEP 561 marker
├── data/
│   └── erdosproblems/               # Git submodule
├── formal/
│   └── lean/
│       ├── lean-toolchain           # leanprover/lean4:v4.12.0
│       ├── lakefile.lean
│       └── Erdos/                   # Generated Lean files
├── index/
│   └── .gitkeep                     # SQLite file goes here (gitignored)
├── logs/
│   └── .gitkeep                     # Logs go here (gitignored)
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_models.py
│   └── test_lean.py
└── .gitignore
```

### Exact Dependencies (pyproject.toml)

**Single source of truth:** `pyproject.toml` (and `uv.lock`) define the exact tool configuration and dependency versions. `docs/_archive/specs/spec-001-dev-environment-tooling.md` is a frozen snapshot of the v1 scaffolding spec.

At minimum, v1 depends on:
- Runtime: `typer`, `rich`, `pydantic`, `pyyaml`, `jinja2`
- Dev: `pytest`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`

---

## 8) Timeline Implications

Given scope reduction:

| Milestone | Estimate | Deliverable |
|-----------|----------|-------------|
| Scaffolding | 1 day | Repo, CLI skeleton, config |
| Dataset loading | 1 day | YAML parser, models, `list`/`show`/`refs` |
| Lean integration | 2 days | `lean init`/`check`/`formalize` working |
| Basic search | 1 day | SQLite FTS, `search` command |
| **V1.0 complete** | **~5 days** | Core workflow functional |
| Ingestion (arXiv + Crossref) | 2-3 days | `ingest` with arXiv source tarball + best-effort extract; Crossref metadata for DOI |
| Full-text search | 1 day | Chunked extracts in index |
| `erdos ask` | 1-2 days | Basic RAG with Claude |
| **V1.1 complete** | **~10 days total** | Research-usable tool |

---

## 9) Open Questions to Resolve

Before coding starts:

1. **What's the actual schema of problems.yaml?** - See Spec 005; upstream is metadata-only
2. **Which problems have Formal Conjectures entries?** - Should we import those?
3. **What mathlib4 commit works with our chosen Lean version?** - Pin this
4. **Do we need Windows support in v1?** - Affects path handling, Lean setup
5. **Who's the first user beyond us?** - Shapes documentation priorities

---

## 10) Summary: What Changed

| Master Draft Says | Qualification Says |
|-------------------|-------------------|
| "Possibly Docling or Nougat or GROBID" | Skip PDF in v1; PDF conversion is deferred to v2.0+; optional `[pdf]` extra uses Marker (GPL) |
| "Maybe SQLite or Postgres or Qdrant" | SQLite only, period |
| "Perhaps sentence-transformers" | No vectors in v1, BM25 only |
| Vertical slice includes ingestion + LLM | True vertical: show → lean init → formalize → check |
| 15 GitHub issues | 23+ finer-grained issues |
| MCP optional but described in detail | MCP cut from v1 entirely |
| `erdos loop` as v1 feature | Deferred to v1.2+ after manual validation |

**The master draft is the vision. This document is the machete that clears the path to v1.**
