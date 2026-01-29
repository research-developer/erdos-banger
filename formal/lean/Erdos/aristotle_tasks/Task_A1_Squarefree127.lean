/-
  Task A1: Prove Squarefree 127 without native_decide

  Current implementation uses:
    lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by native_decide

  Target: Replace with explicit primality proof
-/

import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Tactic.NormNum

-- The goal: prove this WITHOUT native_decide
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by
  -- 7 * 18 + 1 = 127
  -- 127 is prime, and primes are squarefree
  sorry -- ARISTOTLE: Fill this in

-- Helper: 127 is prime
lemma prime_127 : Nat.Prime 127 := by
  sorry -- ARISTOTLE: Fill this in (should work with norm_num)

-- Alternative approach if norm_num fails on Prime
lemma squarefree_127_explicit : Squarefree 127 := by
  sorry -- ARISTOTLE: Fill this in
