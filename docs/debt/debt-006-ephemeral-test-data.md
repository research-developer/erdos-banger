# DEBT-006: Ephemeral Test Data - No Persistence Verification

**Priority:** P1
**Status:** Open
**Found:** 2026-01-18
**Affects:** Search index, CLI, data workflow

## Problem

Every test creates temporary data that vanishes after test completion. No test proves:
- SQLite index survives restart
- Index can be rebuilt from YAML
- Real `data/` directory workflow works
- Production-like paths function correctly

All tests use pytest's `tmp_path` fixtures, meaning we have zero verification that the system works with persistent storage.

## Evidence

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
2. Path resolution logic has never been tested with real directories
3. Permission issues on real filesystems could surface

## Proposed Resolution

1. Add integration test that:
   - Creates `data/` with fixture YAML
   - Runs `erdos index`
   - Verifies `index/problems.db` is created
   - Restarts (new process) and runs `erdos list`
   - Verifies data persists

2. Add "golden file" tests:
   - Compare index SQLite schema against known-good snapshot
   - Compare CLI output format against known-good output

3. Document the expected directory structure in README

## Acceptance Criteria

- [ ] At least one test uses real filesystem paths (not `tmp_path`)
- [ ] Test proves data survives simulated "restart" (new process)
- [ ] `data/` and `index/` directories documented in project root
- [ ] Golden file comparison exists for at least one output format
