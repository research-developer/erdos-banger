# Problem 848 Refactor Notes (SSOT)

**Date:** 2026-01-29
**Last Updated:** 2026-01-31
**Status:** ✅ PHASE 6 IN PROGRESS — 10 of 17 items complete (6.2/6.3/6.6/6.7/6.8/6.9/6.10/6.11/6.14/6.15 + 6.1 partial)
**Scope:** This document is the SSOT for the **Problem 848 Lean formalization**.

---

## ⚠️ Important: What We Formalized

**Original Erdős Problem 848:** Is the maximum size of a set $A ⊆ \{1, …, N\}$ such that $ab + 1$ is never squarefree always at most $|A_7(N)|$ = $⌊(N+18)/25⌋$? (**For ALL N**)

**What Sawhney Proved (2025):** The asymptotic result — there exists $N_0$ such that for all $N ≥ N_0$, the bound holds. The paper does not compute an explicit $N_0$.

**What We Formalized:** Sawhney's asymptotic theorem:
```lean
theorem erdos_848_asymptotic : ∃ N₀ : ℕ, ∀ N ≥ N₀, Erdos848 N
```

| Aspect | Status |
|--------|--------|
| Asymptotic result (∃ N₀, ∀ N ≥ N₀) | ✅ **Formally proved** |
| Original conjecture (∀ N) | ❌ **Still open** |
| Explicit N₀ value | ❌ **Not computed** (would require effectivizing bounds) |
| Computational verification (N ≤ 5000) | ✅ **No counterexamples** (greedy search, 2026-01-31) |

This is a **partial result**, consistent with how erdosproblems.com marks Problem 848 as "decidable" based on Sawhney's work.

---

## Current State (2026-01-31)

| Metric | Value |
|--------|-------|
| Total lines | **5455** |
| Build time | ~14-15 min |
| `sorry` | **0** ✅ |
| `native_decide` | **0** ✅ |
| Build status | **PASSES** ✅ (verified 2026-01-31) |

```bash
lake -d formal/lean build Erdos.Problem848_REFACTOR
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

### Section Map (verified 2026-01-31)

| Section | Lines | Description |
|---------|-------|-------------|
| 1 | 70-117 | Core definitions |
| 2 | 118-167 | Mod 25 divisibility lemmas |
| 3 | 168-328 | Sieve building blocks |
| 4 | 329-424 | Cross-residue constraints |
| 5 | 425-624 | Density lemmas |
| 6 | 625-1026 | Helper lemmas |
| 6.5 | 1027-1081 | Small modular facts (computation) |
| 7 | 1082-2265 | Finite verification (no native_decide) |
| 8 | 2266-2287 | SawhneyMain statement (Prop) |
| 9 | 2288-2384 | Glue theorems |
| 9.5 | 2385-2932 | Quantitative bounds 🔥 (8M heartbeats × 2) |
| 9.8 | 2933-3203 | Bridge lemmas |
| 9.9 | 3204-3490 | More small modular facts |
| 9.95 | 3491-3603 | Generic sieve cardinality bounds |
| 10 | 3604-5443 | `sawhney_main` 🔥 (~1823 lines) |
| 11 | 5444-5455 | Final statements |

### Dependency Flow

```mermaid
flowchart TD
    S1["(1-5) Core defs + Mod lemmas + Sieve blocks"] --> S6
    S6["(6-7) Helpers + Finite checks"] --> S10
    S8["(8-9) Statement layer + Glue"] --> S10
    S95["(9.5) Computation 🔥<br/>natToNum, prime lists, huge ℚ sums"] --> S10
    S10["(10) sawhney_main 🔥<br/>~1823 lines, case split tree"] --> S11
    S11["(11) Final wrapper"]
```

**Bottlenecks:**
1. **Section 9.5** (lines 2385-2932) — 2× 8M heartbeats
2. **Section 10** — `sawhney_main` is ~1823 lines (lines 3621-5443)

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
| 10M | 1 | **0** | ✅ DONE |
| 8M | 0 | **2** | Current (lines 2604, 2613) |

**Result:** All 20M caps reduced to 8M.

---

## Remaining Structural Debt (Future Polish — Optional)

For Mathlib submission, these would improve the file further:

| Debt | Current | Target | Priority |
|------|---------|--------|----------|
| **Scoped maxHeartbeats** | All 9 uses scoped with `in` | ✅ DONE | DONE |
| **Case lemmas** | All 4 case lemmas extracted | ✅ DONE | DONE |
| **High heartbeats in 9.5** | 2× 8M (lines 2604, 2613) | Lower where possible | LOW |
| ~~**Computation isolation**~~ | ~~Mixed with proof~~ | ~~Separate files~~ | ~~WONTFIX~~ — keep single file for external consumers |

---

## Phase 6: External Reviewer Feedback (2026-01-30)

An external Mathlib-style review identified additional refactoring opportunities:

### 6.1 Top-Level Sieve Bound Lemma (HIGH PRIORITY)

**Issue:** Lines ~4500-5300 repeat the sieve density bound logic 4+ times (for Astar, A7, A18).

**Current:** We extracted `have` helpers inside `sawhney_main`, but the algebraic manipulation converting `∑ (N/(k*p²)+1)` to real bounds is still duplicated.

**Proposed:** Extract a top-level lemma:

```lean
lemma sieve_set_card_bound {N k : ℕ} {P : Finset ℕ} {S : Finset ℕ}
    (h_subset : S ⊆ P.biUnion (fun p => (Finset.range N).filter (fun n => k * p^2 ∣ n))) :
    (S.card : ℝ) ≤ (N : ℝ) * (∑ p ∈ P, (1 : ℝ) / (k * (p : ℝ)^2)) + (P.card : ℝ) := by
  sorry -- Move algebraic rearrangement here
```

**Impact:** Could save ~300-500 lines.

### 6.2 Finite Verification Streamlining (MEDIUM PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** `no_five_in_candidates_100` now defines a local `clash` helper (`formal/lean/Erdos/Problem848_REFACTOR.lean:1918`)
and uses it throughout the case split, collapsing repeated `hsprop x hx y hy hsq` boilerplate.

```lean
have clash : ∀ x y, x ∈ s → y ∈ s → Squarefree (x * y + 1) → False := by
  intro x y hx hy hsq
  exact hsprop x hx y hy hsq
```

**Impact:** Improves readability and removes fragile `simpa` casts in the finite verification proof.

### 6.3 Named Constants (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Introduced named density constants at the start of `sawhney_main` and replaced the
corresponding magic numbers in the final density bounds.

```lean
let C_diag : ℝ := (1 : ℝ) / 1750
let C_off : ℝ := 163 / 25000
let C_no5 : ℝ := 413 / 25000
```

**Note:** Added explicit `*_num` helper inequalities (`simpa [C_*]`) before `nlinarith` so the
tactic sees concrete numerals.

### 6.4 Tactic Hygiene (LOW PRIORITY)

| Issue | Location | Suggestion |
|-------|----------|------------|
| `simp_all +decide` overuse | Sections 2-3 | Use `simp only [ZMod.natCast_...]` + `ring` |
| `interval_cases n` (100 goals) | `diag_cand_100` | Consider `fin_cases` on `Fin 100` |
| `grind` usage | `density_single_prime` | Prefer `simp only [mem_filter, mem_range]` |

### 6.5 Naming Conventions (LOW PRIORITY)

| Current | Mathlib Style |
|---------|---------------|
| `hA7A_sub_A` | `A7_subset_A` |
| `hA78_bound` | `card_A7_A18_bound` |
| `primesUpTo` | `primesLe` |
| `DiagonalCandidates` | `DiagonalSieve` |
| `A7A` / `A18A` | `A₇A` / `A₁₈A` (subscripts) or `A_in₇` / `A_in₁₈` |

---

## Phase 6.5: Additional Reviewer Feedback (2026-01-30)

A second round of detailed review identified more refactoring opportunities:

### 6.6 Factor "prime ≤ N" Sub-Argument (MEDIUM PRIORITY)

✅ **Implemented** (2026-01-31)

**Issue:** The same `p ≤ N` derivation repeated throughout `sawhney_main`, typically from
`p^2 ∣ X` and `X < N^2`, followed by a `by_contra` / `pow_le_pow_left` contradiction.

**Fix:** Extracted a reusable helper lemma and replaced all occurrences.

**Definition (in file):**

```lean
lemma prime_le_of_sq_dvd_lt_sq {p N X : ℕ}
    (hXpos : 0 < X) (hXlt : X < N ^ 2) (hp2 : p ^ 2 ∣ X) : p ≤ N := by
  -- contradiction using `p^2 ≤ X < N^2`
```

**Location:** `formal/lean/Erdos/Problem848_REFACTOR.lean:3537`

**Call sites replaced:** 14 occurrences (lines 3876, 3977, 4108, 4161, 4302, 4366, 4519, 4583,
4712, 4775, 5018, 5086, 5223, 5287).

**Impact:** ~40-60 lines saved; removed local `by_contra hpge` / `nlinarith` one-offs used only
to get `p ≤ N`.

### 6.7 Factor "p ≠ 2 Because Odd" Micro-Proof (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Extracted a small helper lemma and replaced the long parity/`4 ∤ ...` blocks.

```lean
lemma prime_ne_two_of_sq_dvd_odd {p n : ℕ} (hn : n % 2 = 1) (hp2 : p ^ 2 ∣ n) : p ≠ 2 := by
  intro h; subst h
  have : 2 ∣ n := dvd_trans (by decide : 2 ∣ 4) (by simpa using hp2)
  omega
```

**Location:** `formal/lean/Erdos/Problem848_REFACTOR.lean:3493`

**Call sites replaced:** 4 (lines 4241, 4297, 4506, 4690).

**Impact:** ~20-30 lines saved, removes fragile parity sub-derivations.

### 6.8 Unify 7/18 Residue Duplicate Lemmas (MEDIUM PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Factored the residue-7 / residue-18 duplicates into parameterized lemmas:
- `mod25_divisibility_of_residue` (`formal/lean/Erdos/Problem848_REFACTOR.lean:122`) → wrappers `mod25_divisibility` / `_18`
- `cross_residue_not_div_25_of_residue` (`formal/lean/Erdos/Problem848_REFACTOR.lean:333`) → wrappers `cross_residue_not_div_25` / `_18`
- `must_have_other_prime_square_of_residue` (`formal/lean/Erdos/Problem848_REFACTOR.lean:395`) → wrappers `must_have_other_prime_square` / `_18`
- `cross_residue_7_18_not_div_25` simplified to call `cross_residue_not_div_25_of_residue`
  (`formal/lean/Erdos/Problem848_REFACTOR.lean:3081`)

**Impact:** Removes duplicate proofs while preserving existing lemma names/signatures at call sites.

### 6.9 Unify A₇_card and A₁₈_card (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Added a general counting lemma for `Finset.range` and rewrote both card lemmas as one-liners.

```lean
lemma card_range_filter_mod25_eq (r : ℕ) (hr : r ≤ 24) (N : ℕ) :
    ((Finset.range N).filter (fun n => n % 25 = r)).card = (N + (24 - r)) / 25 := by
  -- general proof
```

Then `A₇_card` and `A₁₈_card` become `by simpa [A₇]` / `by simpa [A₁₈]`.

**Location:** `formal/lean/Erdos/Problem848_REFACTOR.lean:2291`

**Impact:** ~30 lines saved, better API and less duplication.

### 6.10 Factor "p ∣ b → Filter Empty" Helper (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Extracted helper lemmas for the "if p ∣ b then filter is empty" pattern:
- `not_sq_dvd_mul_add_one_of_prime_dvd_left` — core impossibility lemma
- `filter_empty_of_prime_dvd_left` — filter version
- `filter_empty_of_prime_dvd_left_of_pred` — filter with predicate version

**Location:** `formal/lean/Erdos/Problem848_REFACTOR.lean:3093-3117`

**Impact:** ~20 lines saved, cleaner `off_count_modEq*_le'` lemmas.

### 6.11 Unify N=50 and N=100 Finite-Check Theorems (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Added a shared lemma `problem_848_small` and rewrote both theorems to call it.

```lean
lemma problem_848_small {N k : ℕ} (hA7_card : (A₇ N).card = k)
    (cand : Finset ℕ) (hdiag : DiagonalCandidates N = cand)
    (hno : ∀ s : Finset ℕ, s ⊆ cand → s.card = k.succ → ¬ NonSquarefreeProductProp s) :
    ∀ A : Finset ℕ, A ⊆ Finset.range N → NonSquarefreeProductProp A →
      A.card ≤ (A₇ N).card := by
  -- unified proof (subset extraction + contradiction)
```

**Location:** `formal/lean/Erdos/Problem848_REFACTOR.lean:2231`

**Impact:** ~20 lines saved.

### 6.12 ℚ→ℝ Cast and Scale Helper (MEDIUM PRIORITY)

**Issue:** Repeated blocks (~4120–4135, ~4331–4359, ~4557–4595, ~4764–4796, ~5330–5352) that:
1. Have `hQ : (∑ ... : ℚ) ≤ ...`
2. Cast to ℝ via `Rat.cast_le`
3. Rewrite `∑ 1/(k*p²)` as `(1/k)*∑ 1/p²`
4. Multiply by `1/k` and finish with `nlinarith`

**Proposed:**

```lean
have scale_sum_inv_sq_le_of_rat
    (P : Finset ℕ) (k : ℝ) (C : ℚ)
    (hQ : (∑ p ∈ P, (1:ℚ)/(p^2:ℚ)) ≤ C) (hk : 0 < k) :
    (∑ p ∈ P, (1:ℝ)/(k * (p:ℝ)^2)) ≤ (1/k) * (C : ℝ) := by
  -- unified cast + scale logic
```

**Impact:** Could merge with 6.1 sieve bound work for ~300-500 lines total.

### 6.13 Pull Numerical Contradictions into Named Haves (LOW PRIORITY)

**Issue:** Each major case has a long block culminating in:
```lean
have hA_lt : (A.card : ℝ) < ... := by ...; exact (not_lt_of_ge hdense) hA_lt
```

Appears with different constants in:
- A* empty branch (~4113–4157)
- "exists even in A*" (~4329–4391)
- "odd-only" subcases (~5321–5400)

**Proposed:** Per-case helpers:

```lean
have density_contradiction_caseX : False := by
  -- full numerical contradiction
exact density_contradiction_caseX.elim
```

**Impact:** Flattens indentation, makes case-tree pop out visually.

### 6.14 Paper Case Label Comments (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Added clear `CASE 0/1/2/3` header blocks inside `sawhney_main`, aligned with the
paper’s case split.

### 6.15 Namespace Hygiene: `private` Markers (LOW PRIORITY)

✅ **Implemented** (2026-01-31)

**Fix:** Marked internal scaffolding as `private` (squarefree/non-squarefree witnesses, list
constants, computed list bridges, coarse-sum lemmas, `natToNum`, etc.) to keep the public
namespace clean.

### 6.16 Specific `simp only` Targets (LOW PRIORITY)

**Issue:** Big-heartbeat lemmas use broad `simp`:
- `diagPrimesCoarse_sum_eq` (~line 2643) — 8M heartbeats
- `no5PrimesCoarse_sum_eq` (~line 2652) — 8M heartbeats

**Proposed:** Replace `simp (config := ...) [..]` with `simp (config := ...) only [..]` and minimal lemma set.

**Impact:** May reduce heartbeats from 8M to 6-7M, more stable across Mathlib versions.

### 6.17 Replace `simp_all` in Dense Lemmas (LOW PRIORITY)

**Issue:** `card_filter_mod_pair_le` (~478–567) uses `simp_all +decide` many times in nested branches.

**Proposed:** Replace with explicit destructuring:

```lean
rcases Finset.mem_filter.1 hn with ⟨hn_range, hn_mod⟩
-- keep simp [Nat.ModEq] in controlled spots
```

**Impact:** Easier to audit, less brittle.

---

### Phase 6 Summary Table

| ID | Item | Status | Est. Lines Saved |
|----|------|--------|------------------|
| 6.1 | `sieve_set_card_bound` top-level lemma | ⚠️ PARTIAL (Section 9.95 exists) | 100-200 remaining |
| 6.2 | `clash` helper for finite verification | ✅ DONE | 50-100 |
| 6.6 | `prime_le_of_sq_dvd_lt_sq` helper | ✅ DONE | 40-60 |
| 6.7 | `prime_ne_two_of_sq_dvd_odd` | ✅ DONE | 20-30 |
| 6.8 | Unify 7/18 residue lemmas | ✅ DONE | 50-80 |
| 6.9 | Unify `A₇_card`/`A₁₈_card` | ✅ DONE | 30 |
| 6.10 | `filter_empty_of_prime_dvd_left` | ✅ DONE | 20 |
| 6.11 | Unify N=50/N=100 theorems | ✅ DONE | 20 |
| 6.12 | `scale_sum_inv_sq_le_of_rat` helper | ⏳ TODO (merged w/ 6.1) | — |
| 6.3 | Named constants | ✅ DONE | readability |
| 6.4 | Tactic hygiene (general) | ⏳ LOW | stability |
| 6.5 | Naming conventions | ⏳ LOW | cleanliness |
| 6.13 | `density_contradiction_*` helpers | ⏳ LOW | readability |
| 6.14 | Paper case label comments | ✅ DONE | readability |
| 6.15 | `private` markers | ✅ DONE | namespace |
| 6.16 | `simp only` in 8M lemmas | ⏳ LOW | heartbeats |
| 6.17 | Replace `simp_all` in dense lemmas | ⏳ LOW | stability |

**Next priority items:**
1. 6.1/6.12: Complete sieve bound unification (larger, may need care)
2. 6.13: Pull numerical contradictions into named helpers (readability)
3. 6.16: `simp only` in 8M lemmas (stability / heartbeats)

**Cosmetic polish (optional):**
- 6.4: Tactic hygiene (general)
- 6.5: Naming conventions

---

### Phase 4 Complete: `sawhney_main` Case Lemmas ✅

All 4 case lemmas extracted as local `have` statements inside `sawhney_main`:
- `case_Astar_empty` (line 4012) ✅
- `case_Astar_nonempty_exists_even` (line 4220) ✅
- `case_Astar_all_odd_exists_even_in_A78` (line 4452) ✅
- `case_all_odd` (line 4867) ✅

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
| 8M heartbeats | `8000000` | **2** (lines 2642, 2651) |
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

**The formalization of Sawhney's asymptotic theorem is complete and production-ready.**

> ⚠️ This proves the *asymptotic* result (∃ N₀, ∀ N ≥ N₀), not the full Erdős conjecture (∀ N). See "What We Formalized" section above.

- 0 sorry, 0 native_decide, 0 axioms
- Builds cleanly in ~12-13 min
- All density bound duplicates extracted to helpers
- All Astar bound duplicates extracted to helpers
- All 4 case lemmas extracted (Phase 4 complete)
- All heartbeat options properly scoped with `in`
- No 40M or 20M heartbeat caps remaining
- Phase 5: 20M → 8M reduction complete

**Remaining work is optional polish for Mathlib submission:**
1. ~~Reduce 20M heartbeat caps~~ ✅ DONE (now 8M)
2. 2× 8M heartbeat caps remain (lines 2642, 2651) — likely irreducible for computation-heavy lemmas

**Phase 6 Progress (2026-01-31):**

| Status | Count | Items |
|--------|-------|-------|
| ✅ DONE | 6 | 6.2, 6.6, 6.7, 6.8, 6.9, 6.10 |
| ⚠️ PARTIAL | 1 | 6.1 (sieve bounds exist, may need more unification) |
| ⏳ TODO | 10 | 6.3-6.5, 6.11-6.17 |

**Completed refactors saved ~190-300 lines** from original ~5500+ baseline.

**Full list:** See Phase 6 and Phase 6.5 sections above (items 6.1–6.17).

**Architectural decision:** Keep as single file for external consumers. Only decompose if community requests it.
