# Technical Debt 028: Ingest Manifest Churn (Non-idempotent Writes)

**Date:** 2026-01-20
**Status:** Open
**Priority:** P2 (DevX + repo hygiene)
**Impact:** Running `erdos ingest` repeatedly rewrites manifests even when nothing changes, creating noisy diffs and merge conflicts

## Summary

`erdos ingest` writes per-problem manifest files to `literature/manifests/{problem_id:04d}.yaml`. Manifests include `updated_at`. Today, running ingest on a problem can update `updated_at` and rewrite the manifest even when no new metadata was fetched and the manifest contents are otherwise unchanged.

If `literature/manifests/` is intended to be tracked/committed, this creates unnecessary churn. If it is intended to be local-only, it should likely be gitignored (and sample manifests moved to `tests/fixtures/`).

## Evidence

- Manifest location: `src/erdos/core/literature_paths.py:23`
- Atomic writer exists: `src/erdos/core/ingest/service.py:82` (`_write_manifest_atomic`)
- Example tracked manifests currently exist in repo:
  - `literature/manifests/0006.yaml`
  - `literature/manifests/0042.yaml`

Repro (shows churn via timestamp updates):

1. Run (no network, no downloads):
   - `uv run --frozen erdos ingest 6 --no-network --no-download`
2. Observe `literature/manifests/0006.yaml` `updated_at` changes even if entries do not.

## Why This Matters (Clean Code / DevX)

- Non-idempotent writes make it hard to distinguish “real changes” from “touch noise”.
- Contributors can accidentally commit derived artifacts.
- Merge conflicts become likely when multiple people run ingestion.

## Proposed Resolution (choose one direction)

### Option A (Local-only cache)

- Add `literature/manifests/` to `.gitignore`.
- Keep a small golden manifest set under `tests/fixtures/` for deterministic tests.

### Option B (Tracked shared artifacts)

- Only rewrite/update `updated_at` when the manifest content changes.
- Consider separating:
  - `updated_at` (schema/content change), and
  - `last_ingest_attempt_at` (operational metadata) to avoid churn.

## Acceptance Criteria

- Running `erdos ingest <id>` twice with `--no-network --no-download` produces no file diffs when no content changes.
- A clear repository policy exists: whether `literature/manifests/` is tracked or local-only.
- `make ci` remains green.
