/-
  Quick test: Can we prove Prime 127 without native_decide?
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Tactic.NormNum.Prime

-- Test 1: Try norm_num with Prime extension (this is the Mathlib way)
example : Nat.Prime 127 := by norm_num

-- Test 2: Try decide (kernel-only, slower but acceptable)
example : Nat.Prime 127 := by decide

-- Test 3: If above work, chain to Squarefree
example : Squarefree 127 := by
  have h : Nat.Prime 127 := by decide
  exact h.squarefree

-- Test 4: The actual lemma
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by
  have h : Nat.Prime 127 := by norm_num
  simp only [show 7 * 18 + 1 = 127 by norm_num]
  exact h.squarefree
