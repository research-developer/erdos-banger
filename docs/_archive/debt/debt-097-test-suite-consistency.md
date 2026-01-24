# DEBT-097: Test Suite ANSI Handling Inconsistency

**Status:** Fixed
**Priority:** P2 (Medium)
**Created:** 2026-01-24
**Fixed:** 2026-01-24
**Related:** Intermittent CI failures in `--help` output assertions

## Problem

The test suite has inconsistent use of the `strip_ansi` fixture when checking CLI help output. This causes intermittent CI failures when Rich emits ANSI escape codes based on environment variables (`PY_COLORS`, `FORCE_TERMINAL`).

## Resolution

All tests that assert on CLI `--help` output now normalize help text via the `strip_ansi` fixture in `tests/conftest.py`.

## Root Cause

Tests were written at different times by different contributors without a consistent pattern. The `strip_ansi` fixture exists but isn't enforced.

## Impact

- **CI Failures:** Tests fail intermittently when `PY_COLORS=1` is set by pytest
- **Developer Confusion:** Inconsistent patterns make the codebase harder to maintain
- **False Negatives:** Tests may pass locally but fail in CI

## Acceptance Criteria

1. [x] All tests that check CLI `--help` output use `strip_ansi` fixture
2. [x] Documented convention exists (`CLAUDE.md` → “Testing Gotchas”)
