/-
Targeted query for Aristotle: Prove the cross-product constraint.

If a ≡ 7 (mod 25) and b ≢ 7, 18 (mod 25), then ab+1 might be squarefree.
This constrains the structure of extremal sets.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Finset.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.ZMod.Basic

namespace Erdos.Problem848.SieveQuery2

/-- Non-squarefree product property: ab+1 is not squarefree for all a,b in A. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- Key structural lemma: If a ≡ 7 (mod 25) and b ≡ t (mod 25) where t ∉ {7, 18},
    then ab + 1 ≢ 0 (mod 25). -/
lemma cross_residue_not_div_25 (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) : ¬ (25 ∣ a * b + 1) := by
  intro hdiv
  have h0 : ((a * b + 1 : ℕ) : ZMod 25) = 0 :=
    (ZMod.natCast_eq_zero_iff (a * b + 1) 25).2 hdiv
  have haZ : (a : ZMod 25) = 7 := by
    have : a % 25 = 7 % 25 := by
      simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using ha
    exact (ZMod.natCast_eq_natCast_iff' a 7 25).2 this
  have h1 : (7 : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
    have : (a : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_mul, Nat.cast_one] using h0
    simpa [haZ] using this
  have h2 : (7 : ZMod 25) * (b : ZMod 25) = (-1 : ZMod 25) := by
    simpa using (eq_neg_of_add_eq_zero_left h1)
  have h187 : (18 : ZMod 25) * (7 : ZMod 25) = 1 := by native_decide
  have hbZ : (b : ZMod 25) = (7 : ZMod 25) := by
    -- Multiply `7*b=-1` by the inverse of `7` in `ZMod 25` (which is `18`).
    have hmul : (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) =
        (18 : ZMod 25) * (-1 : ZMod 25) := by
      simpa [mul_assoc] using congrArg (fun x => (18 : ZMod 25) * x) h2
    have hb' : (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
      have hmul' : ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
          (18 : ZMod 25) * (-1 : ZMod 25) := by
        calc
          ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
              (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) := mul_assoc _ _ _
          _ = (18 : ZMod 25) * (-1 : ZMod 25) := hmul
      have : (1 : ZMod 25) * (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
        simpa [h187] using hmul'
      simpa using this
    -- `18 * (-1) = -18 = 7` in `ZMod 25`.
    exact hb'.trans (by native_decide : (18 : ZMod 25) * (-1 : ZMod 25) = (7 : ZMod 25))
  have hbmod : b % 25 = 7 := by
    have hb' : b % 25 = 7 % 25 := (ZMod.natCast_eq_natCast_iff' b 7 25).1 hbZ
    simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using hb'
  exact hb.1 hbmod

/-- If b ≡ t (mod 25) with t ∉ {7, 18}, then for ab+1 to not be squarefree,
    it must be divisible by p² for some prime p ≠ 5. -/
lemma must_have_other_prime_square (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) (hnsq : ¬ Squarefree (a * b + 1)) :
    ∃ p : ℕ, Nat.Prime p ∧ p ≠ 5 ∧ p^2 ∣ a * b + 1 := by
  classical
  have hnot : ¬ ∀ p : ℕ, Nat.Prime p → ¬p * p ∣ a * b + 1 := by
    intro hall
    exact hnsq ((Nat.squarefree_iff_prime_squarefree).2 hall)
  -- From `¬ Squarefree`, extract a prime square divisor.
  push_neg at hnot
  rcases hnot with ⟨p, hp, hpp⟩
  have h25 : ¬ (25 ∣ a * b + 1) := cross_residue_not_div_25 a b ha hb
  have hp2 : p ^ 2 ∣ a * b + 1 := by
    simpa [pow_two] using hpp
  refine ⟨p, hp, ?_, hp2⟩
  intro hp5
  subst hp5
  have : 25 ∣ a * b + 1 := by
    simpa [pow_two] using hp2
  exact (h25 this).elim

/-- The fraction of b in a residue class (mod 25) for which ab+1 is squarefree
    is at least ∏_{p≠5}(1 - 1/p²) = 25/(4π²) ≈ 0.633. -/
lemma squarefree_fraction_lower_bound (a : ℕ) (t : ℕ) (ht : t < 25)
    (hcross : t ≠ 7 ∧ t ≠ 18) (N : ℕ) (hN : N ≥ 100) :
    let B := (Finset.range N).filter (fun b => b % 25 = t)
    let sqfree := B.filter (fun b => Squarefree (a * b + 1))
    (sqfree.card : ℚ) / B.card ≥ 1/2 := by
  sorry

end Erdos.Problem848.SieveQuery2
