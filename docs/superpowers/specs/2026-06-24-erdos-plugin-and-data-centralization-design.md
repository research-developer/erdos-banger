# Design: Erdős Plugin + Centralized Data Home

**Date:** 2026-06-24
**Status:** Approved (pending spec review)
**Topic:** Convert `erdos-banger` into an installable Claude Code plugin backed by a fixed `~/.erdos` data home, with the Lean project relocated to its own globally-reachable repo.

## Goal

Make the `erdos` toolkit usable as a Claude Code plugin from **any** working directory, and stop scattering data across repo-relative directories. Two coupled outcomes:

1. **Centralize data** — all runtime data resolves to a fixed home (`~/.erdos`) regardless of `cwd`.
2. **Ship a plugin** — this repo installs via `/plugin`, bundling the existing skills plus thin command wrappers over a globally-installed `erdos` CLI.

## Context & Constraints

- The CLI entry point exists (`pyproject.toml`: `erdos = "erdos.cli:app"`) but is **not on PATH** anywhere today (only `uv run erdos` inside the repo).
- `AppConfig.from_env` (`core/config.py`) already honors per-path overrides: `ERDOS_DATA_PATH`, `ERDOS_INDEX_PATH`, `ERDOS_SUBMODULE_PATH`, `ERDOS_RUN_LOG_PATH`, `ERDOS_REPO_ROOT`.
- **All** "where do files live" decisions funnel through `repo_path()` / `resolve_repo_root()` (`core/repo_root.py`). Its current fallback is `discover_repo_root() or Path.cwd()` — the `cwd` fallback is precisely what breaks plugin-from-anywhere (outside the repo there is no `pyproject.toml` ancestor, so it writes wherever you happen to be).
- The Lean **toolchain** is already installed globally at `~/.elan/bin/{lake,lean,elan}` (just not always on PATH; `erdos lean` already sources `~/.elan/env`).
- The Lean **project** `formal/lean/` is version-controlled research (Problem006/074/848, `Upstream/FormalConjectures`, `aristotle/` outputs) — "lots of Lean modules." It needs elan + a multi-GB mathlib cache; it is not lightweight portable data.
- Conda `math` env exists at `/opt/anaconda3/envs/math`.
- Current `origin` = `https://github.com/The-Obstacle-Is-The-Way/erdos-banger.git`. `gh` is authenticated as user **research-developer** (a user account, confirmed via `gh api user`; `orgs/research-developer` 404s).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Central data home is `~/.erdos`. |
| D2 | This repo becomes an installable Claude Code plugin (`.claude-plugin/` + `commands/` + `skills/`). |
| D3 | CLI is exposed globally via `uv tool install --editable`; bare `erdos` on PATH. |
| D4 | Run the data sync during implementation (network calls expected). |
| D5 | Lean project is **relocated** to `~/.erdos/formal/lean` via history-preserving `git subtree split`, pushed to a new `research-developer/erdos-lean`. |
| D6 | Lean toolchain + CLI work both globally **and** inside `conda activate math`. |
| D7 | Fork `The-Obstacle-Is-The-Way/erdos-banger` → `research-developer/erdos-banger` first; all structural work on a branch. |

## Architecture

### 1. Data-home resolver

Introduce a single resolver for the data base directory. Precedence:

1. `ERDOS_HOME` env var, if set.
2. A discovered repo root (dev escape hatch — someone hacking inside `erdos-banger`).
3. `~/.erdos` (default). **This replaces the old `Path.cwd()` fallback.**

`repo_path(*parts)` re-anchors on this resolver. Per-path env overrides (`ERDOS_DATA_PATH`, `ERDOS_INDEX_PATH`, `ERDOS_SUBMODULE_PATH`, and new `ERDOS_LEAN_PROJECT`) continue to win individually when set.

**Centralized under `~/.erdos/`:**

```
~/.erdos/
  erdos.env                 # exported env (ERDOS_HOME, ERDOS_LEAN_PROJECT, mailto, keys)
  data/problems_enriched.yaml
  data/erdosproblems/        # clone of teorth/erdosproblems (NOT a submodule here)
  literature/{manifests,cache,extracts}/
  index/erdos.sqlite
  logs/runs.jsonl
  formal/lean/               # standalone git repo (see §3)
```

### 2. Lean project resolution

`get_default_lean_project_path()` resolves: `ERDOS_LEAN_PROJECT` env → `<data-home>/formal/lean` → (dev) discovered repo `formal/lean` → clear error if none reachable. The relocated project at `~/.erdos/formal/lean` is the canonical default.

### 3. Fork + Lean relocation (git topology)

**Fork (first):**
- `gh repo fork The-Obstacle-Is-The-Way/erdos-banger --clone=false --remote` → creates `research-developer/erdos-banger`.
- Local remotes after: `origin` → `research-developer/erdos-banger` (the fork), `upstream` → `The-Obstacle-Is-The-Way/erdos-banger`.
- All structural changes land on a feature branch of the fork.

**Lean subtree split (history preserved):**
- `git subtree split --prefix=formal/lean -b lean-split` in the fork.
- `gh repo create research-developer/erdos-lean --private` (empty repo), then push the `lean-split` branch to it as `main`.
- Clone into `~/.erdos/formal/lean`; set `origin` → `research-developer/erdos-lean`, add `upstream` → `research-developer/erdos-banger` so upstream `formal/lean` changes flow in via `git subtree pull --prefix=formal/lean`.
- In the `erdos-banger` fork branch: `git rm -r formal/lean`, add a short `formal/README.md` pointer explaining the relocation + `ERDOS_LEAN_PROJECT`.
- Re-fetch mathlib at the new location: `lake exe cache get` (one-time, heavy). `Upstream/FormalConjectures` is re-fetchable via existing `formal_conjectures` sync.

### 4. Plugin layout

```
.claude-plugin/
  plugin.json               # name: erdos; version; description; author
  marketplace.json          # lists `erdos` plugin, source = this repo
skills/
  erdos/SKILL.md            # moved from .claude/skills/erdos
  erdos-prove/SKILL.md      # moved from .claude/skills/erdos-prove
commands/
  erdos-setup.md            # one-time bootstrap (see §5)
  erdos-sync.md             # wraps `erdos sync all`
  erdos-list.md  erdos-show.md  erdos-search.md  erdos-refs.md
  erdos-ingest.md  erdos-ask.md  erdos-formalize.md  erdos-check.md
```

- Commands are thin markdown wrappers that invoke the global `erdos` CLI with `$ARGUMENTS`.
- No `agents/` (YAGNI — skills already drive the workflow).
- `.codex/skills/` is left untouched for Codex users.
- Install path for the user: `/plugin marketplace add /Users/psentro/git/erdos-banger` → `/plugin install erdos@erdos-banger`.

### 5. CLI + toolchain exposure & `/erdos-setup`

- `uv tool install --editable /Users/psentro/git/erdos-banger` → bare `erdos` on PATH.
- elan on PATH: append `source ~/.elan/env` to the shell profile; verify `erdos lean check` works from an arbitrary cwd **and** inside `conda activate math`. The `erdos lean` wrapper sourcing `~/.elan/env` remains a backstop.
- `/erdos-setup` automates the bootstrap idempotently: create `~/.erdos`, migrate existing local data, ensure the Lean repo is cloned, `uv tool install`, write `~/.erdos/erdos.env`, and print next steps. Safe to re-run.

### 6. Sync execution (during implementation)

After wiring: `erdos sync submodule` (clone upstream into `~/.erdos/data/erdosproblems`), `erdos sync all` (problems + website data), then build the FTS index. Network activity reported back.

## Data Flow (post-change)

```
any cwd → erdos CLI (global) → data-home resolver (ERDOS_HOME | repo | ~/.erdos)
        → ~/.erdos/{data,literature,index,logs}
        → Lean: ERDOS_LEAN_PROJECT | ~/.erdos/formal/lean (standalone repo)
```

## Testing

- Unit tests for the data-home resolver: `ERDOS_HOME` set, repo-discovery, `~/.erdos` default; per-path overrides still win.
- Update tests assuming repo-relative `formal/lean` / `data/` to honor `ERDOS_HOME` / `ERDOS_LEAN_PROJECT`; `requires_lean` integration test targets the relocated project.
- `make ci` green for resolver + plugin changes. Plugin manifest validated (`plugin-validator` agent or `/plugin` load).

## Risks & Mitigations

- **Destructive tree change** (`git rm -r formal/lean`): done on a fork feature branch, never `main`; history preserved in `research-developer/erdos-lean` via subtree split before removal.
- **mathlib re-fetch** at the new location is heavy but one-time (`lake exe cache get`).
- **Two condas on the box** (`~/miniconda3` and `/opt/anaconda3`): target the `math` env under `/opt/anaconda3/envs/math` explicitly; do not assume which `conda` is active.
- **Behavior change** for in-repo devs (data now defaults to `~/.erdos`): mitigated by the `ERDOS_HOME` escape hatch and repo-root discovery tier.

## Out of Scope

- Publishing the plugin to a public marketplace.
- Re-homing `.codex/skills`.
- Any change to LLM/API provider wiring beyond carrying existing env vars into `~/.erdos/erdos.env`.

## Sequencing

1. Fork → set remotes → feature branch.
2. Subtree split `formal/lean` → push `research-developer/erdos-lean`.
3. Data-home resolver + `ERDOS_LEAN_PROJECT` + config changes (+ tests).
4. `git rm -r formal/lean` + `formal/README.md` pointer.
5. Plugin scaffold (`.claude-plugin/`, `commands/`, move `skills/`).
6. `uv tool install` + toolchain/env wiring + `/erdos-setup`.
7. Migrate data into `~/.erdos`; run sync; build index.
8. `make ci`; validate plugin install; verify `erdos lean check` from arbitrary cwd.
