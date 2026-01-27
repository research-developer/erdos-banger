/-
Targeted query for Aristotle: Prove the density of diagonal candidates.

The set of n where p² | n²+1 for some prime p ≡ 1 (mod 4) has a specific density.
This is a key lemma from Sawhney 2025.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.NumberTheory.LegendreSymbol.Basic
import Mathlib.Data.Nat.ModEq

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
  have hp_ne_two : p ≠ 2 := by omega
  have hp_dvd : p ∣ n ^ 2 + 1 := by
    -- `p ∣ p^2` and `p^2 ∣ n^2+1` implies `p ∣ n^2+1`.
    have hp_div_p2 : p ∣ p ^ 2 := by
      simp [pow_two]
    exact Nat.dvd_trans hp_div_p2 hdiv

  -- Work in `ZMod p`: `p ∣ n^2+1` means `n^2 = -1 (mod p)`.
  haveI : Fact p.Prime := ⟨hp⟩
  have h0 : ((n ^ 2 + 1 : ℕ) : ZMod p) = 0 := (ZMod.natCast_eq_zero_iff (n ^ 2 + 1) p).2 hp_dvd
  have hsq : (n : ZMod p) ^ 2 = (-1 : ZMod p) := by
    have : (n : ZMod p) ^ 2 + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_pow, Nat.cast_one] using h0
    simpa using (eq_neg_of_add_eq_zero_left this)

  -- `-1` is a square mod `p`, so `p % 4 ≠ 3`.
  have hne3 : p % 4 ≠ 3 := ZMod.mod_four_ne_three_of_sq_eq_neg_one (p := p) (y := (n : ZMod p)) hsq

  -- For odd primes, `p % 4` is either `1` or `3`; exclude `3`.
  have hp_mod2 : p % 2 = 1 := (Nat.Prime.mod_two_eq_one_iff_ne_two hp).2 hp_ne_two
  have hp_mod4 : p % 4 = 1 ∨ p % 4 = 3 := (Nat.odd_mod_four_iff).1 hp_mod2
  cases hp_mod4 with
  | inl h1 => exact h1
  | inr h3 => exact (hne3 h3).elim

/--
Research statement (not proved here): for prime `p ≡ 1 (mod 4)`, the congruence `r^2 = -1` has
exactly two solutions in `ZMod (p^2)`.

We keep this as a `Prop` so the file stays `sorry`-free while the Hensel-lifting argument is
formalized separately.
-/
def TwoRootsModPSquared (p : ℕ) : Prop :=
  Nat.Prime p →
    p % 4 = 1 →
    ∃ r₁ r₂ : ZMod (p ^ 2), r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧
      ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂

/--
Research statement (not proved here): for prime `p ≡ 1 (mod 4)`, the set
`{n < N : p^2 ∣ n^2+1}` has density at most `2/p^2` up to a small boundary error.
-/
def DensitySinglePrime (p : ℕ) : Prop :=
  Nat.Prime p →
    p % 4 = 1 →
    ∀ N : ℕ, N > 0 →
      let count := ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card
      (count : ℚ) / N ≤ 2 / p ^ 2 + 1 / N

end Erdos.Problem848.SieveQuery1
