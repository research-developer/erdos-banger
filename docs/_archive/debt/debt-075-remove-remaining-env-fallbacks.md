# DEBT-075: Remove Remaining Env Fallbacks Outside `AppConfig`

**Status:** Fixed
**Priority:** P3 (Minor - improve when touching nearby code)
**Found:** 2026-01-23
**Found By:** Codebase audit (config consistency)
**Fixed:** 2026-01-23
**Commit:** 292124f

---

## Summary

`src/erdos/core/config.py` is the SSOT for environment-based configuration. Most
call sites now thread config via `AppConfig`/`AppContext`. This deck tracked
the remaining `os.environ`/`os.getenv` reads that were scattered across the
codebase.

This was not an immediate correctness bug, but it made behavior harder to reason
about (and harder to test) because configuration was read from multiple places.

---

## Resolution

As of 292124f:

- All direct `os.environ` / `os.getenv` reads were removed from `src/` and routed
  through `AppConfig` (SSOT), including in `ProblemLoader`, `SearchIndex`,
  `RunLogger`, OpenAlex config, ingest orchestration, Aristotle config, and MCP
  wiring.
- Added `build_subprocess_env()` in `src/erdos/core/config.py` for subprocess
  env overrides (so modules don’t need to copy `os.environ` directly).
- Added a regression guard test:
  `tests/unit/core/test_dependencies.py::test_no_env_reads_outside_app_config`.

## Explicit Allowlist

These env touches are intentional and remain allowed:

- `src/erdos/core/config.py`: SSOT for environment variables
- `src/erdos/core/pdf/converter.py`: `TORCH_DEVICE` (external tool integration)

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

1. No `os.environ` / `os.getenv` reads exist under `src/` outside the allowlist.
2. The regression guard test fails if a new env read is introduced.
3. `make ci` passes.
