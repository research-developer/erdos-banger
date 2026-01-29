import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Card

set_option maxRecDepth 10000 in
def primes500 : Finset ℕ := (Finset.range 500).filter Nat.Prime

set_option maxRecDepth 10000 in
lemma primes500_card : primes500.card = 95 := by decide
