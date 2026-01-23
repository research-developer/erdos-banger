# DEBT-075: Remove Remaining Env Fallbacks Outside `AppConfig`

**Status:** Open
**Priority:** P3 (Minor - improve when touching nearby code)
**Found:** 2026-01-23
**Found By:** Codebase audit (config consistency)

---

## Summary

`src/erdos/core/config.py` is the SSOT for environment-based configuration. Most
call sites now thread config via `AppConfig`/`AppContext`, but a small set of
legacy helpers still read `os.environ` directly.

This is not an immediate correctness bug, but it makes behavior harder to reason
about (and harder to test) because configuration can come from multiple places.

---

## Evidence (Current Env Reads Outside `core/config.py`)

These are acceptable *today* as transitional/backwards-compatibility paths, but
they should not be used by new call sites:

- `src/erdos/core/problem_loader.py` (`ProblemLoader.from_default()`)
- `src/erdos/core/search/facade.py` (`SearchIndex.from_default()`)
- `src/erdos/core/run_logger.py` (`RunLogger.__init__()`, `get_run_logger()`)
- `src/erdos/core/providers/crossref.py` (`CrossrefProvider.from_env()`)
- `src/erdos/core/providers/openalex.py` (`OpenAlexProvider.from_env()`)
- `src/erdos/core/clients/openalex.py` (`OpenAlexConfig.from_env()`, `OpenAlexClient.__init__()`)
- `src/erdos/core/ingest/app.py` (`get_repo_root()`, `prepare_mailto()`)
- `src/erdos/core/aristotle.py` (`validate_aristotle_config()` reads `ARISTOTLE_API_KEY` / `ERDOS_ARISTOTLE_COMMAND`)

Intentional non-`AppConfig` env usage that should remain (external tooling):

- `src/erdos/core/pdf/converter.py` (`TORCH_DEVICE`)

---

## Why This Matters

- **Testability:** core services become deterministic when config is explicit.
- **DIP/OCP:** environment is a concrete infrastructure detail; pushing it to the
  composition root reduces hidden coupling.
- **Policy clarity:** CLI should be the place where env/flags are merged, not
  deep helpers.

---

## Proposed Fix

1. Make the remaining `from_env()` / `from_default()` helpers delegate to
   `AppConfig.from_env()` internally (or accept `AppConfig` explicitly).
2. Tighten call sites so production paths never rely on these legacy reads.
3. Add a lightweight audit check (non-gating at first) that flags new `os.environ`
   reads outside `core/config.py` and a short allowlist.

---

## Acceptance Criteria

1. New code does not introduce `os.environ` reads outside `src/erdos/core/config.py`
   (except allowlisted cases like `TORCH_DEVICE`).
2. The CLI composition root remains the only place that merges env + CLI flags.
3. `make ci` passes.
