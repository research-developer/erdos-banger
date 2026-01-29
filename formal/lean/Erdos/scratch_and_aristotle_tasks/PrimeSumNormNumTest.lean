import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.Field.Basic
import Mathlib.Data.Rat.Defs
import Mathlib.Tactic.NormNum.BigOperators
import Mathlib.Tactic.NormNum.Prime

open scoped BigOperators

namespace PrimeSumNormNumTest

def primeCutoff : ℕ := 50

def primesUpTo (B : ℕ) : Finset ℕ :=
  (Finset.range (B + 1)).filter Nat.Prime

def diagPrimesCoarse : Finset ℕ :=
  (primesUpTo primeCutoff).filter (fun p => p % 4 = 1 ∧ 13 ≤ p)

-- Let's see if norm_num can compute this sum for small cutoff.
example :
    (∑ p ∈ diagPrimesCoarse, (1 : ℚ) / (p ^ 2 : ℚ)) =
      (1 : ℚ) / (13^2 : ℚ) + (1 : ℚ) / (17^2 : ℚ) + (1 : ℚ) / (29^2 : ℚ) + (1 : ℚ) / (37^2 : ℚ) + (1 : ℚ) / (41^2 : ℚ) := by
  decide
