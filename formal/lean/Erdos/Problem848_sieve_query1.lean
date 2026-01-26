/-
Targeted query for Aristotle: Prove the density of diagonal candidates.

The set of n where p² | n²+1 for some prime p ≡ 1 (mod 4) has a specific density.
This is a key lemma from Sawhney 2025.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Real.Basic

namespace Erdos.Problem848.SieveQuery1

/-- A number n is a "diagonal candidate" if n²+1 is NOT squarefree. -/
def isDiagonalCandidate (n : ℕ) : Prop := ¬ Squarefree (n * n + 1)

/-- The diagonal candidates up to N. -/
def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

/-- Decidability instance for filtering. -/
instance (n : ℕ) : Decidable (isDiagonalCandidate n) := by
  unfold isDiagonalCandidate
  infer_instance

/-- Key fact: If p² | n²+1 for prime p, then p ≡ 1 (mod 4).
    This is because -1 must be a quadratic residue mod p. -/
lemma prime_sq_divides_implies_one_mod_four (p n : ℕ) (hp : Nat.Prime p) (hp2 : p > 2)
    (hdiv : p^2 ∣ n^2 + 1) : p % 4 = 1 := by
  sorry

/-- For prime p ≡ 1 (mod 4), there are exactly 2 residue classes r mod p²
    such that r² ≡ -1 (mod p²). -/
lemma two_roots_mod_p_squared (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) :
    ∃ r₁ r₂ : ZMod (p^2), r₁ ≠ r₂ ∧ r₁^2 = -1 ∧ r₂^2 = -1 ∧
    ∀ r : ZMod (p^2), r^2 = -1 → r = r₁ ∨ r = r₂ := by
  sorry

/-- The density of integers n where p² | n²+1 is 2/p² for each prime p ≡ 1 (mod 4). -/
lemma density_single_prime (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) (N : ℕ) (hN : N > 0) :
    let count := ((Finset.range N).filter (fun n => (p^2 : ℕ) ∣ n^2 + 1)).card
    (count : ℚ) / N ≤ 2 / p^2 + 1 / N := by
  sorry

end Erdos.Problem848.SieveQuery1
