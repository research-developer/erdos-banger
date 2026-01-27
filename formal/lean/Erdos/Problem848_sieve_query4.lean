/-
Targeted query for Aristotle: Extend finite verification to N=500.

This is pure computation: verify that no 21-element subset of `DiagonalCandidates(500)` has the
non-squarefree product property. Since `|A₇(500)| = 20` and `A₇(500)` satisfies the property,
this would show the conjectured bound is sharp at N = 500.
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree

namespace Erdos.Problem848.FiniteN500

/-- Non-squarefree product property. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

instance (A : Finset ℕ) : Decidable (NonSquarefreeProductProp A) := by
  unfold NonSquarefreeProductProp
  infer_instance

/-- Diagonal candidates: n where n²+1 is not squarefree. -/
def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

/-- A₇(N) = {n < N : n ≡ 7 (mod 25)} -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- The non-squarefree property is hereditary: subsets inherit it. -/
lemma nonSquarefreeProductProp_subset {A B : Finset ℕ} (hAB : A ⊆ B)
    (hB : NonSquarefreeProductProp B) : NonSquarefreeProductProp A := by
  intro a ha b hb
  exact hB a (hAB ha) b (hAB hb)

/-- Any set with the property is contained in `DiagonalCandidates N` (diagonal condition). -/
lemma prop_implies_diag_candidates (A : Finset ℕ) (N : ℕ) (hAsub : A ⊆ Finset.range N)
    (hAprop : NonSquarefreeProductProp A) : A ⊆ DiagonalCandidates N := by
  intro a ha
  simp only [DiagonalCandidates, Finset.mem_filter]
  constructor
  · exact hAsub ha
  · exact hAprop a ha a ha

/-- Compute |A₇(500)| = 20 (elements: 7, 32, 57, ..., 482) -/
lemma A7_500_card : (A₇ 500).card = 20 := by native_decide

/-- Hypothesis: no 21-element subset of `DiagonalCandidates(500)` has the non-squarefree product
property.

This is a *computational* claim intended for external proof (e.g. SAT / certificates). We record
it as a `Prop` so this file remains `sorry`-free. -/
def No21InCandidates500 : Prop :=
  ∀ (s : Finset ℕ), s ⊆ DiagonalCandidates 500 → s.card = 21 → ¬ NonSquarefreeProductProp s

/-- Main theorem for N=500, conditional on `No21InCandidates500`. -/
theorem problem_848_N500 (h_no21 : No21InCandidates500) :
    ∀ A : Finset ℕ, A ⊆ Finset.range 500 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 500).card := by
  intro A hAsub hAprop
  by_contra h
  have hgt : (A₇ 500).card < A.card := lt_of_not_ge h
  rw [A7_500_card] at hgt
  have hcard21 : 21 ≤ A.card := by
    simpa using (Nat.succ_le_iff.2 hgt)
  have hex : ∃ s : Finset ℕ, s ⊆ A ∧ s.card = 21 := by
    exact Finset.exists_subset_card_eq hcard21
  obtain ⟨s, hs_sub, hs_card⟩ := hex
  have hs_prop : NonSquarefreeProductProp s := nonSquarefreeProductProp_subset hs_sub hAprop
  have hA_sub_cand : A ⊆ DiagonalCandidates 500 :=
    prop_implies_diag_candidates A 500 hAsub hAprop
  have hs_sub_cand : s ⊆ DiagonalCandidates 500 := Finset.Subset.trans hs_sub hA_sub_cand
  exact h_no21 s hs_sub_cand hs_card hs_prop

end Erdos.Problem848.FiniteN500
