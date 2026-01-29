/-
Test file for proving numbers are NOT squarefree.
Goal: Eliminate native_decide from pair_32_43_works

Numbers to prove NOT squarefree:
- 1025 = 5² × 41 = 25 × 41
- 1377 = 3⁴ × 17 = 81 × 17
- 1850 = 2 × 5² × 37 = 50 × 37
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.NormNum.Prime

-- Verify factorizations
#check (1025 : ℕ)  -- 5² × 41
#check (1377 : ℕ)  -- 3⁴ × 17
#check (1850 : ℕ)  -- 2 × 5² × 37

example : 5^2 * 41 = 1025 := by norm_num
example : 3^4 * 17 = 1377 := by norm_num
example : 2 * 5^2 * 37 = 1850 := by norm_num

-- Method 1: Direct approach via Squarefree definition
-- Squarefree n means ∀ m, m^2 ∣ n → m = 1

lemma not_squarefree_1025 : ¬ Squarefree 1025 := by
  intro h
  have hdiv : 5^2 ∣ 1025 := by norm_num
  have := h 5 hdiv
  norm_num at this

lemma not_squarefree_1377 : ¬ Squarefree 1377 := by
  intro h
  have hdiv : 3^2 ∣ 1377 := by norm_num
  have := h 3 hdiv
  norm_num at this

lemma not_squarefree_1850 : ¬ Squarefree 1850 := by
  intro h
  have hdiv : 5^2 ∣ 1850 := by norm_num
  have := h 5 hdiv
  norm_num at this

-- Now test the full NonSquarefreeProductProp approach
-- We need: ∀ a ∈ {32, 43}, ∀ b ∈ {32, 43}, ¬ Squarefree (a * b + 1)
