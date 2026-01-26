# End-to-End (E2E) Testing Plan

E2E tests in `erdos-banger` should validate real CLI invocation (subprocess), filesystem side effects, and cross-process persistence. They are the last line of defense against regressions that unit/integration tests can miss (packaging issues, env var wiring, default paths, exit codes, JSON contract, etc.).

## What We Have Today

- E2E suite lives in `tests/e2e/`.
- Current coverage is intentionally light:
  - `erdos show` happy path + common errors
  - Search index persistence across two separate processes

This is good foundation, but it does not cover most real user workflows.

## E2E Test Principles (Keep Them “Banger”)

1. Prefer **JSON-mode assertions** (`--json`) for stability.
2. Assert on **exit codes** and **schema keys**, not exact human-formatted output.
3. Avoid network and paid APIs in default E2E (no `requires_network` by default).
4. Avoid heavyweight Lean builds in default E2E; if needed, mark as `requires_lean`.
5. Ensure tests run from a **non-repo working directory** (the E2E harness uses `cwd=tmp_path`) to catch accidental “assumes you ran from repo root” bugs.
6. Keep runtime low; E2E should remain a fast confidence layer, not a second CI pipeline.

## Recommended E2E Scenarios (Prioritized)

### P0: CLI Contract & Global Flags

- `erdos --help` / `erdos <cmd> --help` are non-crashing and do not print tracebacks.
- `--json` output is valid JSON for core commands.
- Invalid input produces **usage exit code 2** (Typer/Click contract).
- `--log-level` rejects invalid values and does not silently accept junk.

### P1: Core Research Workflow (No Network)

- `erdos list` / `erdos show`:
  - JSON schema stable, exit codes correct
- `erdos search --build-index`:
  - builds `index/erdos.sqlite` under the working directory and returns results
- `erdos ask --no-llm`:
  - returns deterministic structure (`answer: null`, sources present after index build)
- `erdos logs`:
  - after running a command, logs are written and `erdos logs --json` returns entries
- `erdos research` workspace:
  - `research init → note → status → synthesize` across multiple invocations (filesystem persistence)

### P2: “Graceful Failure” for Optional Paid/Network Features

These should be runnable without network by asserting *clean failure modes*:

- `erdos research exa search` with missing `EXA_API_KEY`:
  - exits with ConfigError (no traceback)
- `erdos lean prove` with missing `ARISTOTLE_API_KEY`:
  - exits with ConfigError (no traceback)

### P3: Lean & Sync (Heavier / Optional)

These are valuable but can be slower or depend on toolchain state:

- `erdos lean init` + `erdos lean formalize <id>` + `erdos lean check <file>` (mark `requires_lean`)
- `erdos sync all --dry-run` with test fixtures (requires deterministic inputs; avoid live scraping)

## Fixture & Harness Guidance

### Use the Existing E2E Harness

Prefer `tests/e2e/conftest.py::cli_runner`:

- Runs `uv run erdos ...` as a subprocess (true E2E)
- Uses isolated `tmp_path` for filesystem writes (index, logs, research workspace)
- Overrides `ERDOS_DATA_PATH` to a fixture-backed dataset

### When New Fixtures Are Needed

The unit/integration suite already has strong fixtures for:

- arXiv/Crossref/Exa/S2/zbMATH parsing (`tests/fixtures/*_responses/`)
- sync HTML parsing (`tests/fixtures/sync/**`)
- Lean “toy repo” verification (`tests/fixtures/sync/proof_repo/**`)

E2E expansion will likely need only small **filesystem fixtures**, e.g.:

- minimal manifests under `literature/manifests/`
- minimal research workspace seed files (if required)

Prefer generating these in tests (write small YAML/MD files) unless they’re reused across multiple test modules.

## Where to Track Work

If E2E coverage is expanded, track it as a debt deck in `docs/_debt/` with concrete acceptance criteria and commit hashes.
