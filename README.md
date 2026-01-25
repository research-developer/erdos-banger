# erdos-banger

CLI-first toolkit for collaborative research on Erdos problems, from literature to Lean formalization.

## What This Is

A research harness for the Erdős problems dataset curated by the mathematical community (upstream: https://github.com/teorth/erdosproblems). The goal: provide infrastructure that helps human researchers and AI agents systematically work through these problems.

**The pipeline:**
1. **Problem data** - Load and query problem metadata (status, prizes, tags, references)
2. **Literature ingestion** - Fetch reference metadata from arXiv/Crossref, cache legal open-access content
3. **Search index** - SQLite FTS5 for keyword search across problems and literature
4. **RAG Q&A** - Ask questions about specific problems with citation-grounded answers
5. **Lean formalization** - Generate theorem skeletons, compile, and iterate on proofs

**What it's not:**
- Not an "AI solver" claiming automatic breakthroughs - it's research infrastructure
- Not a web app - CLI-first, designed for automation and agent integration
- Not storing paywalled content - only metadata and legal open-access material

## Current Status

| Component | Status | Spec |
|-----------|--------|------|
| CLI scaffold (list, show, refs, search) | Done | [Spec 004](docs/_archive/specs/spec-004-cli-architecture.md) |
| Problem loader | Done | [Spec 005](docs/_archive/specs/spec-005-problem-loader.md) |
| Search index (SQLite FTS5) | Done | [Spec 006](docs/_archive/specs/spec-006-search-index.md) |
| Lean integration (init, check, formalize) | Done | [Spec 007](docs/_archive/specs/spec-007-lean-integration.md) |
| Presenter cleanup | Done | [Spec 009](docs/_archive/specs/spec-009-architecture-cleanup.md) |
| Ingest command (arXiv + Crossref) | Done | [Spec 010](docs/_archive/specs/spec-010-ingest-command.md) |
| Ask command (RAG + LLM) | Done | [Spec 011](docs/_archive/specs/spec-011-ask-command.md) |
| Loop command (iterative proofs) | Done | [Spec 012](docs/_archive/specs/spec-012-loop-command.md) |

## Quickstart

```bash
# Clone with submodule
git clone https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git
cd erdos-banger
git submodule update --init --recursive

# Install dependencies (requires uv: https://docs.astral.sh/uv/)
uv sync

# Optional: enable the [pdf] extra (installs GPL-licensed tooling; opt-in)
# See docs/_archive/specs/spec-019-pdf-conversion.md for policy and rationale.
uv sync --extra pdf

## Data

By default, `erdos` uses a built-in sample dataset so the CLI works out of the box.

# Optional: create a local dataset override (editable copy)
cp tests/fixtures/sample_problems.yaml data/problems_enriched.yaml

# Verify it works
make smoke
uv run erdos --version
uv run erdos list --status open --limit 5
uv run erdos show 6

# Build the search index (and search)
uv run erdos search "prime arithmetic progression" --build-index
# Subsequent searches reuse the persisted index
uv run erdos search "prime arithmetic progression"

# Lean integration (requires elan: https://github.com/leanprover/elan)
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
├── docs/_specs/         # Specs (current + master docs)
└── tests/               # Unit and integration tests
```

## Contributing

We welcome contributions. The project uses:
- **Python 3.11+** with strict typing (mypy)
- **uv** for dependency management
- **ruff** for linting and formatting
- **pytest** for testing

```bash
# Run the full check suite
uv run ruff check .
uv run ruff format . --check
uv run mypy src/
uv run pytest -m "not requires_lean and not requires_network"
```

See `docs/_specs/` for detailed design documents and the v1.2+ roadmap.

## Documentation

- [Docs Index](docs/INDEX.md) - Getting started, developer guides, architecture, and project docs
- [Master Vision](docs/_specs/master-vision.md) - Full architecture and roadmap
- [Specs Index](docs/_specs/README.md) - Design specs (mostly archived)

## License

Apache-2.0 (matching the upstream erdosproblems dataset)

Optional dependencies:
- The `[pdf]` extra installs `marker-pdf` (GPL-licensed). Installing it locally is opt-in; distributing builds that include it may trigger GPL obligations. See `docs/_archive/specs/spec-019-pdf-conversion.md`.
