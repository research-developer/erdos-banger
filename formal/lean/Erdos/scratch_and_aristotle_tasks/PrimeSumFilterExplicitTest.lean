import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.Field.Basic
import Mathlib.Analysis.PSeries
import Mathlib.Tactic.NormNum.BigOperators

open scoped BigOperators
open scoped Finset

namespace PrimeSumFilterExplicitTest

def primesUpTo50 : Finset ℕ := {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47}

def diagPrimes50 : Finset ℕ := primesUpTo50.filter (fun p => p % 4 = 1 ∧ 13 ≤ p)

def diagSum50 : ℚ := (1124082757541 : ℚ) / (94526092337209 : ℚ)

example : (∑ p ∈ diagPrimes50, (1 : ℚ) / (p ^ 2 : ℚ)) = diagSum50 := by
  simp [diagPrimes50, primesUpTo50, diagSum50]
  norm_num
