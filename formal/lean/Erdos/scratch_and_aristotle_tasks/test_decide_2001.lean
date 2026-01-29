import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Finset.Card

set_option maxRecDepth 50000 in
def primes2001 : Finset ℕ := (Finset.range 2001).filter Nat.Prime

set_option maxRecDepth 50000 in
lemma primes2001_card : primes2001.card = 303 := by decide
