# Bug: Lean skeleton template uses outdated Mathlib import path

**Priority:** P2
**Status:** Fixed
**Found:** 2026-01-26
**Fixed:** 2026-01-26
**Commit:** (pending)

## Description

The `erdos lean formalize` command generates Lean skeletons that fail to compile because the template uses an outdated Mathlib import path.

## Steps to Reproduce

```bash
uv run erdos lean formalize 848
uv run erdos lean check formal/lean/Erdos/Problem848.lean
```

## Expected Behavior

The generated skeleton should compile successfully.

## Actual Behavior

Build fails with:
```
error: no such file or directory (error code: 2)
  file: .lake/packages/mathlib/Mathlib/Algebra/BigOperators/Group/Finset.lean
error: bad import 'Mathlib.Algebra.BigOperators.Group.Finset'
```

## Root Cause

In current Mathlib4, `Mathlib.Algebra.BigOperators.Group.Finset` is a **directory** containing submodules, not a single file. The correct import is `Mathlib.Algebra.BigOperators.Group.Finset.Basic`.

Mathlib underwent a restructuring where many modules were split into submodules, changing single-file imports into directory-based module hierarchies.

## Fix

Changed `src/erdos/templates/lean_skeleton.j2` line 20:

**Before:**
```lean
import Mathlib.Algebra.BigOperators.Group.Finset
```

**After:**
```lean
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
```

## Verification

```bash
# After fix
uv run erdos lean formalize 848
uv run erdos lean check formal/lean/Erdos/Problem848.lean
# Output: ✓ Erdos/Problem848.lean compiled successfully
```

## Related

- [Mathlib4 BigOperators.Group.Finset docs](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Algebra/BigOperators/Group/Finset.html)
- Mathlib module restructuring (ongoing since 2024)
