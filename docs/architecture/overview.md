# Architecture Overview

`erdos-banger` is a CLI-first research workbench. The CLI is thin glue; core logic lives in `src/erdos/core/`.

## High-Level Structure

```text
src/erdos/
├── cli.py              # Typer entry point, global flags
├── commands/           # CLI adapters (Typer + Rich)
└── core/               # Core domain + services (bounded contexts)
```

### Composition Root

- `src/erdos/core/context.py` builds an `AppContext` from `AppConfig`.
- Commands use `src/erdos/commands/app_context.py:get_app_context()` to access the cached `AppContext`.

### Ports and Adapters

- Protocol ports live in `src/erdos/core/ports.py`.
- External IO (HTTP clients, subprocesses) is concentrated in bounded contexts (e.g., `core/clients/`, `core/lean/`).

## Bounded Contexts (Core)

Core is organized by domain:

- `core/problem_loader.py` — load enriched problem datasets
- `core/search/` — SQLite FTS search + indexing
- `core/ingest/` — literature ingestion and persistence
- `core/clients/` — HTTP clients (arXiv, Crossref, OpenAlex, Exa, Semantic Scholar, zbMATH)
- `core/research/` — filesystem research workspace (records, synthesis, status)
- `core/lean/` — Lean project helpers, runner, prover integration
- `core/loop/` — iterative Lean proof loop
- `core/llm/` — task-level routing to external LLM commands

## Output Contracts

- JSON output is wrapped in `CLIOutput` (see `src/erdos/core/models/output.py`).
- Exit codes are centralized in `src/erdos/core/exit_codes.py`.

## Code Health Guardrails

The repo enforces LOC/function-size thresholds via `scripts/audit_code_health.py`. Exemptions must be tracked in `docs/debt/`.
