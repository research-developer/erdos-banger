/-
This file was edited by Aristotle.

Lean version: leanprover/lean4:v4.24.0
Mathlib version: f897ebcf72cd16f89ab4577d0c826cd14afaafc7
This project request had uuid: 00841910-d928-4d0c-94e5-9125c45202a6

To cite Aristotle, tag @Aristotle-Harmonic on GitHub PRs/issues, and add as co-author to commits:
Co-authored-by: Aristotle (Harmonic) <aristotle-harmonic@harmonic.fun>
-/

/-
Self-contained (Mathlib-only) setup for Erdős Problem #848 (Erdős–Sárközy).

This file exists to be submitted to the Aristotle API: it inlines the core
definitions used by our project file `Problem848_experimental.lean` without
importing any local modules.

The target is the asymptotic stability statement from Sawhney (2025), recorded
as `SawhneyMain`. We end with a single `sorry`:

  theorem sawhney_main : SawhneyMain := by
    sorry

Everything else is definitional scaffolding.
-/

import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Real.Basic


namespace Erdos.Problem848.Combined

/-- A set `A` has the non-squarefree product property if `a*b+1` is not squarefree
for all `a, b ∈ A`. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- Candidate extremal set: `{n < N : n ≡ 7 (mod 25)}` using `Finset.range N`. -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- Alternative candidate: `{n < N : n ≡ 18 (mod 25)}` using `Finset.range N`. -/
def A₁₈ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 18)

/-- The exact statement we need from Sawhney (2025), parameterized by constants. -/
def SawhneyMainAt (η : ℝ) (N₀ : ℕ) : Prop :=
  0 < η ∧ η < (1 / 25 : ℝ) ∧
    ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1 / 25 - η) * (N : ℝ) →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N)

/-- Paper-level existential version: there exist `η > 0` and `N₀` making `SawhneyMainAt` true. -/
def SawhneyMain : Prop :=
  ∃ η : ℝ, ∃ N₀ : ℕ, SawhneyMainAt η N₀

/- Aristotle failed to find a proof. -/
theorem sawhney_main : SawhneyMain := by
  sorry

end Erdos.Problem848.Combined
