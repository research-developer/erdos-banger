import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.Order.Field.Basic
import Mathlib.Analysis.PSeries
import Mathlib.Tactic.NormNum.BigOperators
import Mathlib.Tactic.NormNum.Prime
import Mathlib.Tactic.Simproc.Factors
import Mathlib.Data.Nat.Factors

open scoped BigOperators

namespace PrimeSumSimprocProofTest

lemma natPrime_iff_primeFactorsList_eq_singleton (n : ℕ) :
    Nat.Prime n ↔ n.primeFactorsList = [n] := by
  constructor
  · intro hn
    simpa using Nat.primeFactorsList_prime hn
  · intro h
    have : n ∈ n.primeFactorsList := by
      simpa [h]
    exact Nat.prime_of_mem_primeFactorsList this

-- Use primeFactorsList (computable by simproc) as the predicate.
def primesUpToPF (B : ℕ) : Finset ℕ :=
  (Finset.range (B + 1)).filter (fun n => n.primeFactorsList = [n])

def diagPrimesPF (B : ℕ) : Finset ℕ :=
  (primesUpToPF B).filter (fun p => p % 4 = 1 ∧ 13 ≤ p)

example : (primesUpToPF 20).card = 8 := by
  -- primes ≤ 20 are 2,3,5,7,11,13,17,19
  native_decide

-- Can we compute the diag sum for B=50?
example :
    (∑ p ∈ diagPrimesPF 50, (1 : ℚ) / (p ^ 2 : ℚ)) =
      (1 : ℚ) / (13^2 : ℚ) + (1 : ℚ) / (17^2 : ℚ) + (1 : ℚ) / (29^2 : ℚ) + (1 : ℚ) / (37^2 : ℚ) + (1 : ℚ) / (41^2 : ℚ) := by
  classical
  -- Rewrite the filtered sum as a range sum with an indicator.
  -- This avoids needing to reduce the finset itself.
  have :
      (∑ p ∈ diagPrimesPF 50, (1 : ℚ) / (p ^ 2 : ℚ)) =
        ∑ p in Finset.range 51,
          if (p.primeFactorsList = [p] ∧ p % 4 = 1 ∧ 13 ≤ p) then (1 : ℚ) / (p ^ 2 : ℚ) else 0 := by
    simp [diagPrimesPF, primesUpToPF, Finset.sum_filter]
  -- Now everything is a sum over `range`, and the `if` conditions are decidable by simp+simproc.
  -- `simp` reduces each branch and `norm_num` finishes.
  -- (This is intended as a prototype for the `B=2000` computations.)
  simpa [this] using (by
    -- unfold the right-hand side and compute
    -- TODO: see if `simp`+`norm_num` can close it
    simp)
