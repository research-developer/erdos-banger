# DEBT-006: Ephemeral Test Data - No Persistence Verification

**Priority:** P1
**Status:** Fixed
**Found:** 2026-01-18
**Fixed:** 2026-01-18
**Commit:** a47d9f2,57cf739
**Affects:** Search index, CLI, data workflow

## Resolution

- Added an end-to-end persistence test that builds the default `index/erdos.sqlite` and reuses it in a new process.
- Added tracked `data/` and `index/` directories (and gitignored `data/problems_enriched.yaml`) so the project-root layout exists by default.
- Added a golden-file style regression test using `tests/fixtures/lean_outputs/` samples.

## Problem (before fix)

Many tests create temporary data that vanishes after test completion. While we do cover index build/rebuild logic in `tmp_path`, we have no test that proves:
- SQLite index survives a simulated "restart" (new process / new `SearchIndex`) when using the default `index/erdos.sqlite` path
- The default `data/` + `index/` workflow works using persistent, project-root paths (not just ephemeral test directories)
- Production-like paths function correctly (e.g., relative paths from repo root, filesystem permissions)

Filesystem-touching tests rely on pytest's `tmp_path` fixtures (9/36 test files reference `tmp_path`), meaning we have zero verification that the default persistent workflow works end-to-end.

## Evidence (before fix)

**Missing directories:**
```bash
$ ls -la | grep -E "data|index"
# (no output - neither directory exists on disk)
```

**Tests using ephemeral paths (9 files):**
- `tests/integration/test_cli_commands.py`
- `tests/unit/test_formalizer.py`
- `tests/unit/test_lean_runner.py`
- `tests/integration/test_lean_runner.py`
- `tests/unit/test_problem_loader.py`
- `tests/unit/test_search_index.py`
- `tests/integration/test_search_index.py`
- `tests/e2e/conftest.py`
- `tests/integration/conftest.py`

**No golden file comparisons:**
- No known-good SQLite database to compare index builds
- No known-good Lean output to compare skeleton generation
- No known-good CLI output to compare formatting

## Risk

First real user runs `erdos list` and gets "no data found" or similar error because:
1. Default paths don't exist
2. Path resolution has only been tested inside `tmp_path` (via `monkeypatch.chdir`), not against persistent repo-root directories
3. Permission issues on real filesystems could surface

## Proposed Resolution

1. Add integration test that:
   - Creates `data/` with fixture YAML
   - Runs `erdos search --build-index prime` (or any query)
   - Verifies `index/erdos.sqlite` is created
   - Restarts (new process) and runs `erdos search prime` (without `--build-index`)
   - Verifies the search uses the persisted index (`use_fts: true`) and returns results

2. Add "golden file" tests:
   - Compare index SQLite schema against known-good snapshot
   - Compare CLI output format against known-good output

3. Document the expected directory structure in README

## Acceptance Criteria

- [ ] At least one test uses real filesystem paths (not `tmp_path`)
- [ ] Test proves data survives simulated "restart" (new process)
- [ ] `data/` and `index/` directories documented in project root
- [ ] Golden file comparison exists for at least one output format
