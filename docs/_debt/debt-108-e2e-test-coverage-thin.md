# DEBT-108: End-to-End Test Coverage Is Thin

**Priority:** P2 (Material quality gap; should be scheduled soon)
**Status:** Open
**Found:** 2026-01-26

## Summary

The test suite has strong unit/integration coverage, but the E2E layer is currently too small to reliably catch regressions in:

- real subprocess CLI execution
- environment variable wiring
- default path behavior (`data/`, `index/`, `logs/`, research workspace)
- cross-process persistence
- “no traceback” guarantees at the true process boundary

## Evidence

- E2E suite currently includes:
  - `tests/e2e/test_cli_show.py`
  - `tests/e2e/test_persistent_workflow.py`

This covers `erdos show` and search-index persistence, but not the typical workflows users actually run (search → ask → research workspace → logs, etc.).

## Why This Matters

Integration tests (Typer `CliRunner`) are excellent for fast behavioral coverage, but they can miss issues that only appear when:

1. the CLI is invoked as a real process (subprocess + real environment)
2. files are created relative to the working directory
3. multiple commands are run across separate processes (persistence)

That’s exactly where “stress test” failures often live.

## Proposed Fix

Expand E2E coverage with a small set of fast, deterministic scenarios that:

- default to no-network and no-paid-API operation
- prefer JSON contract assertions (`--json`)
- validate exit codes and stable schema keys
- run from a non-repo working directory (current harness already does this)

**SSOT Plan:** `docs/developer/e2e-testing.md`

## Acceptance Criteria

1. [ ] Add E2E coverage for the core “no-network” workflow:
   - `erdos list` (JSON contract)
   - `erdos search --build-index` (creates `index/erdos.sqlite`)
   - `erdos ask --no-llm` (answer is null; sources present after index build)
   - `erdos research init/note/status/synthesize` (filesystem persistence across invocations)
   - `erdos logs` (logs written after a command; readable in JSON)
2. [ ] Add E2E “graceful failure” checks for missing paid/network configuration:
   - `erdos research exa search` without `EXA_API_KEY` returns ConfigError (no traceback)
   - `erdos lean prove` without `ARISTOTLE_API_KEY` returns ConfigError (no traceback)
3. [ ] Keep E2E runtime reasonable under `make ci` (avoid slow/Lean/network by default).
4. [ ] Ensure new E2E tests use `strip_ansi` when asserting on help output.
5. [ ] `make ci` passes after adding tests.

## Notes on Fixtures

No fixture gaps were found for unit/integration parsing (arXiv/Crossref/Exa/S2/zbMATH/sync HTML already have deterministic fixtures under `tests/fixtures/`).

E2E expansion should prefer generating minimal filesystem inputs inside the test using `tmp_path` unless the same fixture is reused across multiple E2E modules.

