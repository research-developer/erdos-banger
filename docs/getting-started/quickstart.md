# Quickstart

Get `erdos` running locally in minutes.

## Install

```bash
git clone https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git
cd erdos-banger
git submodule update --init --recursive

# Requires uv: https://docs.astral.sh/uv/
uv sync

# Optional: configure API keys (gitignored)
cp .env.example .env
```

## Run

```bash
uv run erdos --help
make smoke
```

## Data (What `erdos` loads by default)

Problem data is resolved in this order (see `src/erdos/core/problem_loader.py`):

1. `ERDOS_DATA_PATH` (file or directory)
2. `data/problems_enriched.yaml` (local override; **gitignored**)
3. Built-in sample dataset shipped with the package (`src/erdos/data/problems_enriched.yaml`)
4. `data/erdosproblems/data/problems.yaml` (upstream submodule; metadata-only fallback)

To create a local, editable dataset override:

```bash
cp tests/fixtures/sample_problems.yaml data/problems_enriched.yaml
uv run erdos list --limit 5
```

## Next Steps

- Learn common workflows: [Common Usage](./usage.md)
- Configure API keys and paths: [Configuration](../developer/configuration.md)
- Full command flags: [CLI Reference](../developer/cli-reference.md)
