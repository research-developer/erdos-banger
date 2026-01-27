/-
Targeted query for Aristotle: Prove the corrected Sawhney stability theorem.

The key fix: we require η to be SMALL (η < 1/50), not just positive.
This prevents the trivial counterexample where c=1 makes the size constraint vacuous.

From Sawhney 2025: For η small enough and N large enough, any set A with
|A| ≥ (1/25 - η)N and the non-squarefree product property must be contained
in A₇ or A₁₈.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Real.Basic
import Mathlib.NumberTheory.SelbergSieve

namespace Erdos.Problem848.SawhneyMain

/-- Non-squarefree product property. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- A₇(N) = {n < N : n ≡ 7 (mod 25)} -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- A₁₈(N) = {n < N : n ≡ 18 (mod 25)} -/
def A₁₈ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 18)

/-- The corrected Sawhney stability statement with an explicit smallness constraint on `η`.

This is recorded as a `Prop` (no proof here); proving it requires the sieve/density argument from
Sawhney (2025). -/
def SawhneyStabilityAt (η : ℝ) (N₀ : ℕ) : Prop :=
  0 < η ∧ η < 1 / 50 ∧
    ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1 / 25 - η) * (N : ℝ) →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N)

def SawhneyStability : Prop :=
  ∃ η : ℝ, ∃ N₀ : ℕ, SawhneyStabilityAt η N₀

/-- Key lemma: Cross-residue products are sometimes squarefree.
    If a ≡ 7 (mod 25) and b ≢ 7, 18 (mod 25), then ab+1 might be squarefree.
    This means large sets can't mix residue classes. -/
lemma cross_residue_sometimes_squarefree :
    ∃ a b : ℕ, a % 25 = 7 ∧ b % 25 ≠ 7 ∧ b % 25 ≠ 18 ∧ Squarefree (a * b + 1) := by
  -- 7 * 2 + 1 = 15 = 3 * 5, squarefree!
  use 7, 2
  native_decide

end Erdos.Problem848.SawhneyMain
