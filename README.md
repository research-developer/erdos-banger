# erdos-banger

CLI-first toolkit for collaborative research on Erdős problems — from literature to Lean formalization.

## What This Is

A research harness for the Erdős problems dataset curated by the mathematical community (upstream: https://github.com/teorth/erdosproblems). The goal: provide infrastructure that helps human researchers and AI agents systematically work through these problems.

**The pipeline:**

1. **Problem data** — Load and query problem metadata (status, prizes, tags, references)
2. **Literature ingestion** — Fetch reference metadata from arXiv/Crossref/OpenAlex, cache legal open-access content
3. **Search index** — SQLite FTS5 for keyword search across problems and literature
4. **RAG Q&A** — Ask questions about specific problems with citation-grounded answers
5. **Lean formalization** — Generate theorem skeletons, compile, and iterate on proofs

**What it's not:**
- Not an “AI solver” claiming automatic breakthroughs — it’s research infrastructure
- Not a web app — CLI-first, designed for automation and agent integration
- Not storing paywalled content — only metadata and legal open-access material

## Core Commands

Run `uv run erdos --help` to see the full CLI, but the main workflows are:

- `list`, `show` — browse the Erdős problem dataset
- `search` — keyword search (FTS5); persists an on-disk index
- `refs` — list references; query Semantic Scholar; look up zbMATH
- `ingest` — ingest literature metadata and cache (legal open-access where available)
- `ask` — RAG Q&A (optional LLM; supports `--no-llm` for offline mode)
- `lean` — Lean project init/check/formalize/import/prove helpers
- `research` — per-problem research workspace (notes/leads/hypotheses/tasks/attempts)
- `sync` — sync problem data from multiple sources (website/submodule/proofs/statements)
- `logs`, `dashboard` — run logs + progress dashboard
- `loop` — iterative proof loop (uses an external LLM command)

## Quickstart

```bash
# Clone with submodule
git clone https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git
cd erdos-banger
git submodule update --init --recursive

# Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# Sanity check
make smoke
uv run erdos --help
```

### Data

By default, `erdos` uses a built-in sample dataset so the CLI works out of the box.

To use an editable local dataset override:

```bash
# Optional: create a local dataset override (editable copy)
cp tests/fixtures/sample_problems.yaml data/problems_enriched.yaml
```

Then try a few commands:

```bash
uv run erdos --version
uv run erdos list --status open --limit 5
uv run erdos show 6
```

### Search

Build the search index once (persisted under `index/`):

```bash
# Build the search index (and search)
uv run erdos search "prime arithmetic progression" --build-index
# Subsequent searches reuse the persisted index
uv run erdos search "prime arithmetic progression"
```

### Lean (optional)

Install `elan` (https://github.com/leanprover/elan), then:

```bash
uv run erdos lean init
uv run erdos lean formalize 6
uv run erdos lean check formal/lean/Erdos/Problem006.lean
```

## Project Structure

```text
erdos-banger/
├── src/erdos/           # Python package
│   ├── cli.py           # Typer entry point
│   ├── commands/        # CLI subcommands
│   └── core/            # Business logic (models, loader, index, lean runner)
├── data/
│   ├── problems_enriched.yaml   # Optional local dataset override (gitignored)
│   └── erdosproblems/           # Upstream submodule (metadata only)
├── formal/lean/         # Lean 4 project
│   ├── Erdos/           # Problem formalizations
│   ├── lakefile.lean    # Lake configuration
│   └── lean-toolchain   # Pinned Lean version
├── literature/          # Reference manifests and cache (cache is gitignored)
├── index/               # SQLite search index (gitignored)
├── docs/                # Docs index, guides, architecture, ADRs
└── tests/               # Unit and integration tests
```

## Contributing

We welcome contributions. The project uses:

- **Python 3.11+** with strict typing (mypy)
- **uv** for dependency management
- **ruff** for linting and formatting
- **pytest** for testing

```bash
# CI-equivalent (fast; skips slow/Lean/network tests)
make ci

# Full local CI (includes test-all + smoke)
make ci-full
```

### Optional extras

- `uv sync --extra pdf` installs PDF conversion tooling (opt-in; includes GPL-licensed components). See `docs/developer/pdf-conversion.md`.
- `uv sync --extra embeddings` installs semantic search dependencies (Sentence Transformers) for `erdos search --semantic` / `--hybrid`.
- `uv sync --extra mcp` installs optional MCP server dependencies

## Documentation

- [Hosted docs](https://the-obstacle-is-the-way.github.io/erdos-banger/)
- [Docs Index](docs/index.md) — start here
- [Quickstart](docs/getting-started/quickstart.md)
- [Usage](docs/getting-started/usage.md)
- [CLI Reference](docs/developer/cli-reference.md)
- [Configuration](docs/developer/configuration.md)
- [Testing](docs/developer/testing.md)
- [E2E Testing](docs/developer/e2e-testing.md)
- [Architecture Overview](docs/architecture/overview.md)

Process docs (for contributors/maintainers):

- Active bug decks: `docs/_bugs/`
- Active debt decks: `docs/_debt/`
- ADRs: `docs/adr/`

## License

Apache-2.0 (matching the upstream erdosproblems dataset)

Optional dependencies:
- The `[pdf]` extra installs `marker-pdf` (GPL-licensed). Installing it locally is opt-in; distributing builds that include it may trigger GPL obligations. See `docs/developer/pdf-conversion.md`.
