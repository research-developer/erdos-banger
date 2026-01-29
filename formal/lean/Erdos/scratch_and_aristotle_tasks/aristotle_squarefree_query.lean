/-
Aristotle Query: Prove composite numbers are squarefree WITHOUT native_decide

Context: We're eliminating native_decide from a Mathlib proof.
We know how to prove primes are squarefree: (by norm_num : Nat.Prime p).squarefree
We know how to prove NOT squarefree: show p² ∣ n, then contradict Squarefree def

Challenge: How to prove a COMPOSITE number IS squarefree?
Example: 10 = 2 × 5 is squarefree (no prime² divides it)

Please fill in the sorry with a proof that doesn't use native_decide or decide.
-/

import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Tactic.NormNum.Prime

-- We can prove primes are squarefree:
example : Squarefree 2 := (by norm_num : Nat.Prime 2).squarefree
example : Squarefree 5 := (by norm_num : Nat.Prime 5).squarefree

-- We can prove NOT squarefree by showing a square divides:
example : ¬ Squarefree 50 := by
  intro h
  have hdiv : 5^2 ∣ 50 := by norm_num
  have := h 5 hdiv
  norm_num at this

-- CHALLENGE: Prove a composite IS squarefree without native_decide
-- 10 = 2 × 5, both prime, so 10 is squarefree

lemma squarefree_10 : Squarefree 10 := by
  sorry

-- If you can solve that, here are more we need:
-- 26 = 2 × 13
-- 37 = prime (easy)
-- 65 = 5 × 13
-- 82 = 2 × 41
-- 101 = prime (easy)
-- 122 = 2 × 61
-- 145 = 5 × 29
-- 170 = 2 × 5 × 17

-- Bonus: Is there a general tactic or approach for this?
