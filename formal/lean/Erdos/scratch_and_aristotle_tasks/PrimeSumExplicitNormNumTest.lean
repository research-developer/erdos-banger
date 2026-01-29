import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.Field.Basic
import Mathlib.Analysis.PSeries
import Mathlib.Tactic.NormNum.BigOperators

open scoped BigOperators
open scoped Finset

namespace PrimeSumExplicitNormNumTest

def diagPrimes50 : Finset ℕ := {13, 17, 29, 37, 41}

def diagSum50 : ℚ := (1124082757541 : ℚ) / (94526092337209 : ℚ)

example : (∑ p ∈ diagPrimes50, (1 : ℚ) / (p ^ 2 : ℚ)) = diagSum50 := by
  -- direct computation over an explicit finset
  simp [diagPrimes50, diagSum50]
  norm_num
