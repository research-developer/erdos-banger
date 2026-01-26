# Configuration Reference

This document describes the configuration surface that is expected to be stable over time.

For all **configuration** env-var reads, the source of truth is
`src/erdos/core/config.py` (`AppConfig.from_env()`), plus LLM routing rules in
`src/erdos/core/llm/tasks.py`.

Some modules may temporarily read/write non-`ERDOS_*` env vars to integrate
third-party tools (e.g., `TORCH_DEVICE` for Marker), but those are not treated
as stable application configuration.

## Global CLI Flags

These are defined in `src/erdos/cli.py`:

- `--json`: machine-readable output (`CLIOutput` envelope)
- `--log-level`: `DEBUG`, `INFO`, `WARN`, `ERROR`
- `--version`: print version

## `.env` Files (Local Development)

For local convenience, the `erdos` CLI loads a `.env` file if present at:

- `${ERDOS_REPO_ROOT}/.env` (if `ERDOS_REPO_ROOT` is set), otherwise
- `./.env` (current working directory)

This loader is intentionally minimal:

- Supports simple `KEY=value` lines (with optional `export ` prefix)
- Supports single/double quoted values
- Strips inline `# comments` for unquoted values
- Does **not** support multiline values or shell expansion
- Does **not** override already-set environment variables

Use the provided template:

```bash
cp .env.example .env
```

## Environment Variables (Core)

| Name | Meaning | Default / Notes |
|------|---------|-----------------|
| `ERDOS_DATA_PATH` | Problems dataset path (file or directory) | If a directory, `problems_enriched.yaml` or `problems.yaml` is searched. |
| `ERDOS_INDEX_PATH` | SQLite search index path | Defaults to `index/erdos.sqlite`. |
| `ERDOS_RUN_LOG_PATH` | Run log JSONL path | Defaults to `logs/runs.jsonl`. |
| `ERDOS_REPO_ROOT` | Repo root used for filesystem workspaces | If unset, some features assume `Path.cwd()` is the repo root. |
| `ERDOS_SUBMODULE_PATH` | Path to `teorth/erdosproblems` submodule | Defaults to `data/erdosproblems`. |
| `ERDOS_MAILTO` / `OPENALEX_EMAIL` | Contact email for polite pools | Used for OpenAlex and other APIs. |
| `ERDOS_LLM_COMMAND` | Global external LLM command | Used as fallback for all LLM tasks. |
| `ERDOS_ARISTOTLE_COMMAND` | Path to `aristotle` CLI | Defaults to `aristotle`. |
| `ARISTOTLE_API_KEY` | Aristotle API key | Used by `erdos lean prove`. |
| `OPENALEX_API_KEY` | OpenAlex API key | Optional (some OpenAlex endpoints work without). |

## Environment Variables (Research APIs + Caches)

| Name | Meaning | Default / Notes |
|------|---------|-----------------|
| `EXA_API_KEY` | Exa Research API key | Required for `erdos research exa …`. |
| `ERDOS_EXA_CACHE_TTL` | Exa cache TTL (hours) | Default `24`. |
| `ERDOS_EXA_CACHE_PATH` | Exa cache directory | Default `literature/cache/exa`. |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key | Optional; some endpoints work without. |
| `ERDOS_S2_CACHE_TTL` | Semantic Scholar cache TTL (days) | Default `7`. |
| `ERDOS_S2_CACHE_PATH` | Semantic Scholar cache directory | Default `literature/cache/s2`. |
| `ERDOS_ZBMATH_CACHE_TTL` | zbMATH cache TTL (days) | Default `30`. |
| `ERDOS_ZBMATH_CACHE_PATH` | zbMATH cache directory | Default `literature/cache/zbmath`. |

## LLM Task Routing (Environment Chains)

LLM execution is vendor-neutral: `erdos` shells out to a command/script. The command is resolved per task type:

- `ask_question`: `ERDOS_LLM_COMMAND_MATH` → `ERDOS_LLM_COMMAND`
- `loop_patch`: `ERDOS_LLM_COMMAND_CODE` → `ERDOS_LLM_COMMAND`
- `tactic_generation`: `ERDOS_LLM_COMMAND_COPILOT` → `ERDOS_LLM_COMMAND_MATH` → `ERDOS_LLM_COMMAND`

See `src/erdos/core/llm/tasks.py`.

## JSON Output Envelope

When `--json` is passed, commands emit a `CLIOutput` envelope (see `src/erdos/core/models/output.py`).

Required shape:

```json
{
  "schema_version": 1,
  "command": "erdos <command>",
  "success": true,
  "data": {},
  "error": null,
  "timestamp": "2026-01-25T00:00:00Z",
  "duration_ms": 123
}
```

On failure: `success=false`, `data=null`, and `error` includes `type`, `message`, and `code`.

## Exit Codes

Defined in `src/erdos/core/exit_codes.py`:

- `0` — success
- `1` — generic error
- `2` — usage error
- `3` — not found
- `4` — network error
- `5` — Lean error
- `10` — configuration error
