/-
Problem 848: Brute-force finite verification attempt

This file attempts to prove problem_848_N50 by exhaustive checking of all
19,600 triples using native_decide. May take a long time or timeout.

Run with: lake build Erdos.Problem848_BruteForce
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Finset.Powerset
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Algebra.BigOperators.Group.Finset.Basic

namespace Erdos.Problem848.BruteForce

/-- A set A has the non-squarefree product property if ab+1 is not squarefree
    for all a, b in A. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- Decidability instance -/
instance (A : Finset ℕ) : Decidable (NonSquarefreeProductProp A) := by
  unfold NonSquarefreeProductProp
  infer_instance

/-- The candidate set A₇ -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- |A₇(50)| = 2 -/
lemma A₇_50_card : (A₇ 50).card = 2 := by native_decide

/-- Property is hereditary to subsets -/
lemma nonSquarefreeProductProp_subset {A B : Finset ℕ} (hAB : A ⊆ B)
    (hB : NonSquarefreeProductProp B) : NonSquarefreeProductProp A := by
  intro a ha b hb
  exact hB a (hAB ha) b (hAB hb)

/-!
## Brute Force Approach

Key insight: If any set A with |A| ≥ 3 had the property, then every 3-element
subset would also have it (by hereditary lemma).

So we need to check: NO 3-element subset of {0,...,49} has the property.

That's C(50,3) = 19,600 checks. Each check evaluates 9 squarefree tests
(3×3 pairs). Total: ~176,400 squarefree computations.
-/

/-- Check that a specific triple does NOT have the property.
    i.e., at least one of the 9 products ab+1 IS squarefree. -/
def tripleHasSquarefreePair (a b c : ℕ) : Bool :=
  Squarefree (a * a + 1) ||
  Squarefree (a * b + 1) ||
  Squarefree (a * c + 1) ||
  Squarefree (b * a + 1) ||
  Squarefree (b * b + 1) ||
  Squarefree (b * c + 1) ||
  Squarefree (c * a + 1) ||
  Squarefree (c * b + 1) ||
  Squarefree (c * c + 1)

/-- Small test: {0, 1, 2} should NOT have the property -/
example : tripleHasSquarefreePair 0 1 2 = true := by native_decide

/-- Small test: {7, 32} (from A₇) with any third element should fail -/
example : tripleHasSquarefreePair 7 32 0 = true := by native_decide
example : tripleHasSquarefreePair 7 32 1 = true := by native_decide
example : tripleHasSquarefreePair 7 32 3 = true := by native_decide

/-- Key lemma: {7, 32} has the property (no squarefree products) -/
example : ¬tripleHasSquarefreePair 7 32 7 = true := by native_decide

/-- But adding ANY third distinct element breaks it -/
-- Testing a few specific cases first to make sure the approach works
example : tripleHasSquarefreePair 7 32 57 = true := by native_decide  -- 57 ≡ 7 (mod 25)

/-!
## The Full Check

WARNING: The following may take a very long time or cause memory issues.
It checks all 19,600 triples.
-/

/-- Check all triples in range N -/
def allTriplesHaveSquarefreePair (N : ℕ) : Bool :=
  (Finset.range N).all fun a =>
    (Finset.range N).all fun b =>
      (Finset.range N).all fun c =>
        a ≥ b || b ≥ c || tripleHasSquarefreePair a b c

/-- All triples {a,b,c} with a < b < c < 50 have at least one squarefree product.

    This is the computational heart of the finite verification.
    If this succeeds, problem_848_N50 follows easily.

    WARNING: This checks 50³ = 125,000 iterations (though most are skipped).
    May take a while. -/
theorem no_triple_works : allTriplesHaveSquarefreePair 50 = true := by
  native_decide

end Erdos.Problem848.BruteForce
