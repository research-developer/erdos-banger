# Aristotle Tasks for Problem 848 Refactoring

**Goal:** Replace remaining `native_decide` calls with explicit proofs acceptable to Mathlib.

**Status:** 43 → 12 `native_decide` (72% reduction achieved manually!)

**Aristotle Version:** Lean 4.24.0 / Mathlib v4.24.0
**Our Project:** Lean 4.27.0 (version mismatch - may need downgrade or separate project)

---

## ✅ COMPLETED (Manual - No Aristotle Needed)

### Task A1: `seven_times_eighteen_plus_one_squarefree` ✅ DONE
```lean
-- Solution: Use norm_num to prove Prime 127, then Nat.Prime.squarefree
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by
  have h : Nat.Prime 127 := by norm_num
  simp only [show 7 * 18 + 1 = 127 by norm_num]
  exact h.squarefree
```

### Task A2: `pair_7_18_fails` ✅ DONE
```lean
-- Solution: Use the squarefree lemma as witness
lemma pair_7_18_fails : ¬ NonSquarefreeProductProp ({7, 18} : Finset ℕ) := by
  intro h
  have h7 : 7 ∈ ({7, 18} : Finset ℕ) := by simp
  have h18 : 18 ∈ ({7, 18} : Finset ℕ) := by simp
  exact h 7 h7 18 h18 seven_times_eighteen_plus_one_squarefree
```

---

## 🔴 REMAINING (12 native_decide calls)

### Category A: Squarefree-based (6 tasks)

| Line | Lemma | Status | Notes |
|------|-------|--------|-------|
| 665 | `pair_32_43_works` | TODO | Need non-squarefree proofs for 1025, 1377, 1850 |
| 696 | `diag_cand_50` | HARD | Set enumeration with Squarefree filter |
| 698 | `diag_cand_100` | HARD | Set enumeration with Squarefree filter |
| 701 | `no_triple_works_50` | HARD | Exhaustive combinatorial search |
| 705 | `no_triple_in_candidates` | HARD | Exhaustive search |
| 710 | `no_five_in_candidates_100` | HARD | Exhaustive search |

### Category B: Large Computation (6 tasks)

| Line | Lemma | Status | Notes |
|------|-------|--------|-------|
| 955 | `diagPrimesCoarse_sum_eq` | VERY HARD | Sum over primes |
| 959 | `offPrimesCoarse_sum_eq` | VERY HARD | Sum over primes |
| 963 | `no5PrimesCoarse_sum_eq` | VERY HARD | Sum over primes |
| 975 | `diagPrimeSumCoarse_bound` | VERY HARD | ~2000-digit integers |
| 996 | `offPrimeSumCoarse_bound` | VERY HARD | ~2000-digit integers |
| 1017 | `no5PrimeSumCoarse_bound` | VERY HARD | ~2000-digit integers |

---

## Next Task: `pair_32_43_works`

Need to prove these are NOT squarefree:
- 32×32+1 = 1025 = 5² × 41
- 32×43+1 = 1377 = 3⁴ × 17
- 43×32+1 = 1377 (same)
- 43×43+1 = 1850 = 2 × 5² × 37

Strategy:
```lean
lemma not_squarefree_1025 : ¬ Squarefree 1025 := by
  intro h
  have : 5^2 ∣ 1025 := by norm_num
  have : IsUnit 5 := h 5 this
  simp at this
```

---

## Aristotle API Approach (If Needed)

1. **Version Issue:** Our project is Lean 4.27.0, Aristotle needs 4.24.0
2. **Options:**
   - Downgrade our project to 4.24.0 (risky)
   - Create separate 4.24.0 project for Aristotle tasks
   - Continue manual refactoring (working well so far!)

3. **If using Aristotle:**
   - Create stubs with `sorry`
   - Submit to API
   - Port solutions back

---

## Key Discovery

**`norm_num` works for primality!**
```lean
example : Nat.Prime 127 := by norm_num  -- Works!
```

This unlocks many Squarefree proofs via `Nat.Prime.squarefree`.
