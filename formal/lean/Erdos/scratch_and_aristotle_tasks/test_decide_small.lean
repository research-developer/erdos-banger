import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Card

-- Test: can decide handle small prime lists?
def smallPrimes : Finset ℕ := (Finset.range 100).filter Nat.Prime

-- Try with 100 numbers
lemma small_test : smallPrimes.card = 25 := by decide
