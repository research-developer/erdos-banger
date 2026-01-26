# DEBT-099: Lean Test Fixture lakefile Syntax Outdated

**Status:** Fixed
**Priority:** P2 (Blocks Lean integration tests)
**Created:** 2026-01-24
**Fix Commit:** 1580514
**Related:** `test-with-lean` CI job, SPEC-035 proof sync

## Problem

The Lean test fixtures at `tests/fixtures/sync/proof_repo/` use deprecated `lakefile.lean` syntax that is incompatible with modern Lake versions (v4.0+).

## Evidence

CI output shows:
```
SKIPPED [1] tests/integration/test_sync_proof.py:134: Build failed (toolchain issue?):
error: ./lakefile.lean:5:2: error: 'version' is not a field of structure 'Lake.PackageConfig'
error: ./lakefile.lean:5:15: error: unexpected token; expected command
```

Current fixture content (`tests/fixtures/sync/proof_repo/with_sorry/lakefile.lean`):
```lean
import Lake
open Lake DSL

package «erdos-test-sorry» where
  version := v!"0.0.1"  -- DEPRECATED: 'version' field removed in Lake v4.0+

@[default_target]
lean_lib Problem347 where
```

## Root Cause

Lake v4.0 removed the `version` field from `PackageConfig`. The fixture was created with an older Lake version.

## Fix

Update both fixtures to use modern lakefile syntax:

```lean
import Lake
open Lake DSL

package «erdos-test-sorry» where
  -- No version field needed

@[default_target]
lean_lib Problem347 where
```

## Acceptance Criteria

1. [x] Update `tests/fixtures/sync/proof_repo/with_sorry/lakefile.lean`
2. [x] Update `tests/fixtures/sync/proof_repo/no_sorry/lakefile.lean`
3. [x] Verify `make test-lean` passes (equivalent to CI's Lean test job)
4. [x] Tests `test_verify_fixture_repo_with_sorry` and `test_verify_fixture_repo_no_sorry` run

## Effort Estimate

~10 minutes
