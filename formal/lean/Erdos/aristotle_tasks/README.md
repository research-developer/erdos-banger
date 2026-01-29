# Aristotle Tasks for Problem 848 Refactoring

**Goal:** Replace 14 `native_decide` calls with explicit proofs acceptable to Mathlib.

**Aristotle Version:** Lean 4.24.0 / Mathlib v4.24.0
**Our Project:** Lean 4.27.0 (may need separate project)

---

## Category A: Squarefree Proofs (8 tasks)

These need explicit primality proofs. Strategy:
1. Prove `Nat.Prime n` using `norm_num [Nat.Prime]`
2. Use `Nat.Prime.squarefree` to get `Squarefree n`

### Task A1: `seven_times_eighteen_plus_one_squarefree`
```lean
-- CURRENT (line 651):
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by native_decide

-- TARGET:
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by
  have h : Nat.Prime 127 := by norm_num [Nat.Prime]
  exact h.squarefree
```

### Task A2: `pair_7_18_fails`
```lean
-- CURRENT (line 654):
lemma pair_7_18_fails : ¬ NonSquarefreeProductProp ({7, 18} : Finset ℕ) := by native_decide

-- NEEDS: Proof that 7*18+1 = 127 is squarefree (prime)
-- Approach: unfold NonSquarefreeProductProp, exhibit witness (7,18), show 127 squarefree
```

### Task A3: `pair_32_43_works`
```lean
-- CURRENT (line 657):
lemma pair_32_43_works : NonSquarefreeProductProp ({32, 43} : Finset ℕ) := by native_decide

-- NEEDS: Proofs that:
-- 32*32+1 = 1025 = 5² × 41 (not squarefree)
-- 32*43+1 = 1377 = 3⁴ × 17 (not squarefree)
-- 43*43+1 = 1850 = 2 × 5² × 37 (not squarefree)
```

### Task A4-A5: `diag_cand_50`, `diag_cand_100`
```lean
-- CURRENT (lines 688, 690):
-- These compute DiagonalCandidates which filters by Squarefree
-- Need to enumerate and prove each element satisfies the predicate
```

### Task A6-A8: Exhaustive search lemmas
```lean
-- Lines 693, 697, 702
-- noTripleWorksIn 50, no_triple_in_candidates, no_five_in_candidates_100
-- These check combinations - need systematic case analysis
```

---

## Category B: Large Computation Proofs (6 tasks)

These involve sums over primes or ~2000-digit number inequalities.

### Task B1-B3: Prime sum equalities (lines 947, 951, 955)
```lean
-- diagPrimesCoarse_sum_eq, offPrimesCoarse_sum_eq, no5PrimesCoarse_sum_eq
-- Strategy: May need interval_cases or explicit summation over primes
```

### Task B4-B6: Large integer inequalities (lines 967, 988, 1009)
```lean
-- diagPrimeSumCoarse_bound, offPrimeSumCoarse_bound, no5PrimeSumCoarse_bound
-- These are inequalities with ~2000-digit numbers
-- Strategy: norm_num with large literal comparison?
```

---

## Approach for Aristotle

1. Create a Lean 4.24.0 project with minimal Mathlib
2. Define stubs for each lemma as `sorry`
3. Submit to Aristotle API to fill in proofs
4. Port successful proofs back to our 4.27.0 project

---

## Priority Order

1. **A1** - Simplest, just prove Prime 127
2. **A2, A3** - Build on A1
3. **B4-B6** - Try norm_num on large integers
4. **A4-A8** - More complex case analysis
5. **B1-B3** - Hardest (sum over prime sets)
