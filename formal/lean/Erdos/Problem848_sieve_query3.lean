/-
Targeted query for Aristotle: Extend finite verification to N=200.

This is pure computation: verify that no 9-element subset of `DiagonalCandidates(200)` has the
non-squarefree product property. Since `|A₇(200)| = 8` and `A₇(200)` satisfies the property,
this would show the conjectured bound is sharp at N = 200.
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Squarefree

namespace Erdos.Problem848.FiniteN200

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

/-- Compute |A₇(200)| = 8 (elements: 7, 32, 57, 82, 107, 132, 157, 182) -/
lemma A7_200_card : (A₇ 200).card = 8 := by native_decide

/-- Compute DiagonalCandidates(200). -/
lemma diag_cand_200 : DiagonalCandidates 200 =
    {7, 18, 32, 38, 41, 43, 57, 68, 70, 82, 93, 99, 107, 117, 118, 132, 143, 157, 168, 182, 193} := by
  native_decide

/-- No 9-element subset of `DiagonalCandidates(200)` has the non-squarefree product property. -/
lemma no_nine_in_candidates_200 :
    ∀ (s : Finset ℕ), s ⊆ DiagonalCandidates 200 → s.card = 9 → ¬ NonSquarefreeProductProp s := by
  native_decide

/-- Main theorem for N=200: max size is at most |A₇(200)| = 8. -/
theorem problem_848_N200 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 200 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 200).card := by
  intro A hAsub hAprop
  -- If A.card ≥ 9, extract a 9-element subset and contradict `no_nine_in_candidates_200`.
  by_contra h
  have hgt : (A₇ 200).card < A.card := lt_of_not_ge h
  -- Rewrite the left side with the computed cardinality.
  rw [A7_200_card] at hgt
  have hcard9 : 9 ≤ A.card := by
    -- 8 < A.card implies 9 ≤ A.card.
    simpa using (Nat.succ_le_iff.2 hgt)
  have hex : ∃ s : Finset ℕ, s ⊆ A ∧ s.card = 9 := by
    exact Finset.exists_subset_card_eq hcard9
  obtain ⟨s, hs_sub, hs_card⟩ := hex
  have hs_prop : NonSquarefreeProductProp s := nonSquarefreeProductProp_subset hs_sub hAprop
  have hA_sub_cand : A ⊆ DiagonalCandidates 200 :=
    prop_implies_diag_candidates A 200 hAsub hAprop
  have hs_sub_cand : s ⊆ DiagonalCandidates 200 := Finset.Subset.trans hs_sub hA_sub_cand
  exact no_nine_in_candidates_200 s hs_sub_cand hs_card hs_prop

end Erdos.Problem848.FiniteN200
