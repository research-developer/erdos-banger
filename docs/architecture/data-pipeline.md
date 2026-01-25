# Data Pipeline

This document explains the concrete data artifacts `erdos` reads and writes.

## Problem Data

Problem datasets are YAML lists of enriched `ProblemRecord` entries (see `src/erdos/core/models/problem.py`).

Resolution order (see `src/erdos/core/problem_loader.py`):

1. `ERDOS_DATA_PATH`
2. `data/problems_enriched.yaml` (local override; gitignored)
3. Built-in sample dataset in the package (`src/erdos/data/problems_enriched.yaml`)
4. `data/erdosproblems/data/problems.yaml` (upstream submodule; metadata-only fallback)

## Literature

Literature artifacts live under `literature/`:

- `literature/manifests/`: per-problem manifests (metadata)
- `literature/cache/`: file caches for external APIs and downloaded artifacts (gitignored)

## Search Index

The search index is an on-disk SQLite database (FTS5):

- Default: `index/erdos.sqlite` (gitignored)
- Built via `erdos search ... --build-index`

## Research Workspace (Filesystem SSOT)

Research state is stored under `research/` (git-tracked by default):

- `research/problems/{id:04d}/`: per-problem workspace
- YAML record files: leads, attempts, hypotheses, tasks
- `SYNTHESIS.md`: deterministic rendered summary

## Lean Artifacts

Lean artifacts live under `formal/lean/`:

- `Erdos/Problem{ID:03d}.lean`: generated skeletons and proofs
- `lakefile.lean` / `lean-toolchain`: pinned toolchain

## Run Logs

Commands write run logs to JSONL:

- Default: `logs/runs.jsonl`
- Loop runs also write to `logs/loop/` (gitignored)
