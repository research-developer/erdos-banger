# Bug 013: `--log-level` flagged as dead code (Invalidated)

**Priority:** P2
**Status:** Invalidated
**Found:** 2026-01-21
**Invalidated:** 2026-01-21
**Commit:** 1d5bd51

## Description

This issue was originally filed as “dead code” because commands do not read `ctx.obj["log_level"]` after startup.

However, `--log-level` is used to configure Python logging at CLI startup, and the codebase emits logs via `logging.getLogger(__name__)` (e.g., `logger.exception`, `logger.warning`, `logger.debug`). The unused context entry is harmless and can be removed as cleanup if desired.

## Evidence

- `src/erdos/cli.py` calls `_configure_logging(log_level)` in the Typer callback.
- Logging is used in multiple modules, including:
  - `src/erdos/commands/search.py`
  - `src/erdos/core/ingest/service.py`
  - `src/erdos/core/lean_runner.py`

## Resolution

Track logging coverage/consistency as technical debt.
