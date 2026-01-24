# DEBT-097: Test Suite ANSI Handling Inconsistency

**Status:** Open
**Priority:** Medium
**Created:** 2026-01-24
**Related:** CI failures on Python 3.11/3.12 help output tests

## Problem

The test suite has inconsistent use of the `strip_ansi` fixture when checking CLI help output. This causes intermittent CI failures when Rich emits ANSI escape codes based on environment variables (`PY_COLORS`, `FORCE_TERMINAL`).

## Evidence

The `conftest.py` provides a `strip_ansi` fixture (line 100-110) for normalizing CLI output, but several tests don't use it:

| File | Line(s) | Test | Issue |
|------|---------|------|-------|
| `tests/test_cli_structure.py` | 17-20 | `test_cli_has_json_flag()` | No `strip_ansi` |
| `tests/integration/test_lean_import.py` | 99-103 | `test_status_help()` | No `strip_ansi` |
| `tests/integration/test_lean_import.py` | 210-216 | `test_import_help()` | No `strip_ansi` |
| `tests/integration/test_lean_import.py` | 521-564 | Inline conditionals | Inconsistent usage |
| `tests/e2e/test_cli_show.py` | 47-52 | `test_show_help()` | Uses custom runner |

## Root Cause

Tests were written at different times by different contributors without a consistent pattern. The `strip_ansi` fixture exists but isn't enforced.

## Impact

- **CI Failures:** Tests fail intermittently when `PY_COLORS=1` is set by pytest
- **Developer Confusion:** Inconsistent patterns make the codebase harder to maintain
- **False Negatives:** Tests may pass locally but fail in CI

## Acceptance Criteria

1. [ ] All tests that check CLI `--help` output use `strip_ansi` fixture
2. [ ] Add linting rule or documented convention for help output tests
3. [ ] Consider creating a helper function: `assert_in_help(output, text)`

## Workaround

Current fix: Individual test files were updated (commit 64aa931) to use `strip_ansi`. Remaining violations should be addressed as part of routine maintenance.

## Effort Estimate

~2 hours to fix remaining violations and add documentation.
