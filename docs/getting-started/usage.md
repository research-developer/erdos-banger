# Common Usage

This page shows the common workflows. For the authoritative flag list, see the generated [CLI Reference](../developer/cli-reference.md) or run `uv run erdos COMMAND --help`.

## Explore Problems

```bash
uv run erdos list --limit 10
uv run erdos show 6
uv run erdos search "arithmetic progressions" --limit 5
```

## Sync Upstream Data (Optional)

The upstream `teorth/erdosproblems` submodule is **metadata-only**. The `sync` commands pull additional sources and update your local dataset.

```bash
uv run erdos sync all
```

## Literature + References

```bash
uv run erdos ingest 6
uv run erdos refs problem 6
```

## Ask (RAG Q&A)

```bash
export ERDOS_LLM_COMMAND="./scripts/llm.sh"
uv run erdos ask 6 "Summarize known approaches."
```

## Lean

```bash
uv run erdos lean init
uv run erdos lean formalize 6
uv run erdos lean check formal/lean/Erdos/Problem006.lean
```

## Loop + Research Workspace

```bash
uv run erdos research init 6
uv run erdos loop run 6 --no-apply
uv run erdos dashboard
```
