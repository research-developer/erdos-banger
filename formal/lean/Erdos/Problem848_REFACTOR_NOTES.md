# Problem 848 Refactor Notes (SSOT)

**Date:** 2026-01-29
**Last Updated:** 2026-01-30
**Status:** ✅ PHASE 5 IN PROGRESS — 20M→10M reduction complete, 2× 10M remaining
**Scope:** This document is the SSOT for the **Problem 848 Lean formalization**.

---

## Current State (2026-01-30)

| Metric | Value |
|--------|-------|
| Total lines | **5421** |
| Build time | ~12-13 min |
| `sorry` | **0** ✅ |
| `native_decide` | **0** ✅ |
| Build status | **PASSES** ✅ |

```bash
lake build Erdos.Problem848_REFACTOR
# Build completed successfully (2755 jobs).
```

---

## ✅ Resolved: Scoped Heartbeat Option (Mathlib Hygiene)

```lean
-- CURRENT (bad):
set_option maxHeartbeats 2000000
theorem sawhney_main : SawhneyMain := by

-- SHOULD BE:
set_option maxHeartbeats 2000000 in
theorem sawhney_main : SawhneyMain := by
```

---

## Architecture Overview

### Section Map (verified 2026-01-30)

| Section | Lines | Description |
|---------|-------|-------------|
| 1 | 70-117 | Core definitions |
| 2 | 118-168 | Mod 25 divisibility lemmas |
| 3 | 169-329 | Sieve building blocks |
| 4 | 330-443 | Cross-residue constraints |
| 5 | 444-643 | Density lemmas |
| 6 | 644-1045 | Helper lemmas |
| 6.5 | 1046-1100 | Small modular facts (computation) |
| 7 | 1101-2280 | Finite verification (no native_decide) |
| 8 | 2281-2302 | SawhneyMain statement (Prop) |
| 9 | 2303-2424 | Glue theorems |
| 9.5 | 2425-2972 | Quantitative bounds 🔥 (10M heartbeats × 2) |
| 9.8 | 2973-3247 | Bridge lemmas |
| 9.9 | 3248-3535 | More small modular facts |
| 10 | 3536-5411 | `sawhney_main` 🔥 (~1876 lines) |
| 11 | 5412-5423 | Final statements |

### Dependency Flow

```mermaid
flowchart TD
    S1["(1-5) Core defs + Mod lemmas + Sieve blocks"] --> S6
    S6["(6-7) Helpers + Finite checks"] --> S10
    S8["(8-9) Statement layer + Glue"] --> S10
    S95["(9.5) Computation 🔥<br/>natToNum, prime lists, huge ℚ sums"] --> S10
    S10["(10) sawhney_main 🔥<br/>~1842 lines, case split tree"] --> S11
    S11["(11) Final wrapper"]
```

**Bottlenecks:**
1. **Section 9.5** (lines 2425-2972) — 2× 10M heartbeats
2. **Section 10** — `sawhney_main` is ~1876 lines (lines 3536-5411)

---

## Completed Phases

### Phase 1: Linter Cleanup ✅

| Metric | Before | After |
|--------|--------|-------|
| Build warnings | ~50 | **0** |
| Tabs | >0 | **0** |
| Deprecated APIs | 1 | **0** |
| `simpa` count | 542 | 486 |

### Phase 2: Density Bound Extraction ✅

| Pattern | Blocks | Helper |
|---------|--------|--------|
| Mod 25 | 8 → 1 | `residue_class_card_bound_of_subset` (line 3623, `have` in `sawhney_main`) |
| Mod 100 | 4 → 1 | `residue_class_card_bound100_of_subset` (line 3663, `have` in `sawhney_main`) |

**Note:** Helpers are `have` statements inside `sawhney_main`, not top-level lemmas.

**Result:** -107 lines, 10 duplicates eliminated.

### Phase 3: Astar Bound Extraction ✅

| Pattern | Before | After | Helper |
|---------|--------|-------|--------|
| Astar mod25 | 3 inline blocks | 1 `have`, 3 uses | `Astar_bound_mod25` (line 3750, inside `sawhney_main`) |
| Astar mod50 | 3 inline blocks | 1 `have`, 3 uses | `Astar_bound_mod50` (line 3854, inside `sawhney_main`) |

**Result:** -78 lines from Phase 2 baseline (5487 → 5409).

### Phase 5: Heartbeat Reduction (In Progress)

| Heartbeat Cap | Before | After | Status |
|---------------|--------|-------|--------|
| 40M | 0 | 0 | N/A |
| 20M | 3 | **0** | ✅ DONE |
| 10M | 1 | **2** | Remaining target |

**Result:** All 20M caps reduced to 10M or lower.

---

## Remaining Structural Debt (Future Polish — Optional)

For Mathlib submission, these would improve the file further:

| Debt | Current | Target | Priority |
|------|---------|--------|----------|
| **Scoped maxHeartbeats** | All 11 uses scoped with `in` | ✅ DONE | DONE |
| **Case lemmas** | All 4 case lemmas extracted | ✅ DONE | DONE |
| **High heartbeats in 9.5** | 2× 10M (lines 2642, 2651) | Lower where possible | MEDIUM |
| ~~**Computation isolation**~~ | ~~Mixed with proof~~ | ~~Separate files~~ | ~~WONTFIX~~ — keep single file for external consumers |

### Phase 4 Complete: `sawhney_main` Case Lemmas ✅

All 4 case lemmas extracted as local `have` statements inside `sawhney_main`:
- `case_Astar_empty` (line 3961) ✅
- `case_Astar_nonempty_exists_even` (line 4170) ✅
- `case_Astar_all_odd_exists_even_in_A78` (line 4408) ✅
- `case_all_odd` (line 4831) ✅

### Case Lemma Tree (Future Target)

If splitting `sawhney_main`, the natural structure is:

```
sawhney_main
├── case_Astar_empty
│   ├── A7A = ∅ → done
│   ├── A18A = ∅ → done
│   └── both nonempty → density contradiction
├── case_Astar_nonempty_exists_even (Case 1)
├── case_Astar_all_odd_exists_even_in_A78 (Case 3)
└── case_all_odd (Case 2: mod 100 split)
```

---

## Mathlib Hygiene Tips

From external reviewer analysis — useful for future polish:

### Performance Profiling

```lean
-- Find slow spots:
set_option profiler true

-- Auto-suggest heartbeat bounds:
#count_heartbeats in
theorem foo : ... := by ...
```

### Simp Optimization

```lean
-- Before (slow):
simp [div_eq_mul_inv, mul_sum, mul_assoc, mul_left_comm, mul_comm]

-- After (use simp? to find minimal set):
simp only [mul_comm]  -- if that's all that's needed
```

---

## Critical Gotchas

### `simpa` → `simp` is NOT simple

```lean
-- WRONG:
simp using h0  -- ERROR: 'using' is not valid with simp

-- CORRECT:
simpa using h0  →  simp at h0  -- different semantics!
```

### Lake builds by FILENAME

```bash
# CORRECT:
lake build Erdos.Problem848_REFACTOR

# WRONG (uses namespace):
lake build Erdos.Problem848_workbench
```

### `decide` on large Finsets explodes

Use List equality + `List.toFinset` instead.

---

## The `natToNum` Breakthrough

Core technique that eliminated all `native_decide`:

```lean
def natToNum : ℕ → Num
  | 0 => 0
  | n + 1 => natToNum n + 1
```

This is **kernel-reducible**, so `(natToNum p).Prime` can be computed by `decide` without `native_decide`.

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| `Problem848.lean` | ✅ Stable | Primary — DO NOT EDIT |
| `Problem848_FINAL.lean` | ✅ Stable | Backup — DO NOT EDIT |
| `Problem848_REFACTOR_BACKUP_PHASE4.lean` | ✅ Stable | Backup after Phase 4 complete — DO NOT EDIT |
| `Problem848_REFACTOR.lean` | 🔄 Active | Sandbox — agent workspace for Phase 5 |

---

## Quick Reference for Agents

### Key Search Patterns

| What | Grep Pattern | Current Count |
|------|--------------|---------------|
| All sorries | `sorry` | **0** |
| Native decide | `native_decide` | **0** |
| Global heartbeats (bad) | `^set_option maxHeartbeats.*[^n]$` | **0** ✅ |
| Scoped heartbeats (ok) | `set_option maxHeartbeats.*in$` | **9** |
| 20M heartbeats | `20000000` | **0** ✅ |
| 10M heartbeats | `10000000` | **2** (lines 2642, 2651) |
| simpa usage | `simpa` | 486 |
| biUnion bounds | `card_biUnion_le` | 7 |

### Verification Commands

```bash
# Build (from repo root)
lake -d formal/lean build Erdos.Problem848_REFACTOR

# Count lines
wc -l formal/lean/Erdos/Problem848_REFACTOR.lean

# Find sorries
grep -n "sorry" formal/lean/Erdos/Problem848_REFACTOR.lean

# Find native_decide
grep -n "native_decide" formal/lean/Erdos/Problem848_REFACTOR.lean

# Find global maxHeartbeats (should be empty now)
grep -n "^set_option maxHeartbeats" formal/lean/Erdos/Problem848_REFACTOR.lean | grep -v " in$"

# Find high heartbeat caps (20M/10M)
grep -n "20000000\|10000000" formal/lean/Erdos/Problem848_REFACTOR.lean | grep maxHeartbeats
```

### Helper Locations Inside `sawhney_main`

All helper `have` statements are defined early in `sawhney_main` (starts line 3541):

| Helper | Line | Purpose |
|--------|------|---------|
| `sum_div_add_one_le` | 3586 | Bound `∑ (N/(k*p²)+1)` |
| `residue_class_card_bound_of_subset` | 3623 | Mod 25 density bound |
| `residue_class_card_bound100_of_subset` | 3663 | Mod 100 density bound |
| `Astar_bound_mod25` | 3750 | A* bound (mod 25) |
| `Astar_bound_mod50` | 3854 | A* bound (mod 50, odd only) |

---

## Summary

**The formalization is mathematically complete and production-ready.**

- 0 sorry, 0 native_decide, 0 axioms
- Builds cleanly in ~12-13 min
- All density bound duplicates extracted to helpers
- All Astar bound duplicates extracted to helpers
- All 4 case lemmas extracted (Phase 4 complete)
- All heartbeat options properly scoped with `in`
- No 40M or 20M heartbeat caps remaining
- Phase 5: 20M → 10M reduction complete

**Remaining work is optional polish for Mathlib submission:**
1. ~~Reduce 20M heartbeat caps~~ ✅ DONE (now 10M)
2. Reduce 2× 10M heartbeat caps (lines 2642, 2651) — may be irreducible for computation-heavy lemmas

**Architectural decision:** Keep as single file for external consumers. Only decompose if community requests it.
