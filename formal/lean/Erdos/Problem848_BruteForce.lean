/-
Problem 848: Brute-force finite verification attempt

This file attempts to prove problem_848_N50 by exhaustive checking.
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
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

/-- |A₇(50)| = 2, so A₇(50) = {7, 32} -/
lemma A₇_50_card : (A₇ 50).card = 2 := by native_decide

/-- A₇(50) = {7, 32} -/
example : A₇ 50 = {7, 32} := by native_decide

/-- A₇(50) has the property -/
example : NonSquarefreeProductProp (A₇ 50) := by native_decide

/-!
## Key Insight

For N=50, A₇(50) = {7, 32} has only 2 elements.
Any 3-element subset with the property would need all pairs to give non-squarefree products.

The question: Does any 3-element subset of {0,...,49} have the property?

If all elements are ≡ 7 (mod 25), then yes. But in {0,...,49}, only {7, 32} satisfy this.
So we need to check if any "mixed" triple works.
-/

/-- Check if a triple {a, b, c} has the property (all 9 products non-squarefree) -/
def tripleHasProperty (a b c : ℕ) : Bool :=
  !Squarefree (a * a + 1) &&
  !Squarefree (a * b + 1) &&
  !Squarefree (a * c + 1) &&
  !Squarefree (b * a + 1) &&
  !Squarefree (b * b + 1) &&
  !Squarefree (b * c + 1) &&
  !Squarefree (c * a + 1) &&
  !Squarefree (c * b + 1) &&
  !Squarefree (c * c + 1)

/-- {7, 32} pair works (both products non-squarefree) -/
example : !Squarefree (7 * 7 + 1) = true := by native_decide   -- 50 = 2 × 5²
example : !Squarefree (7 * 32 + 1) = true := by native_decide  -- 225 = 9 × 25 = 3² × 5²
example : !Squarefree (32 * 32 + 1) = true := by native_decide -- 1025 = 25 × 41 = 5² × 41

/-- Test: {0, 1, 2} does NOT have the property -/
example : tripleHasProperty 0 1 2 = false := by native_decide

/-- Test: {7, 32, 0} does NOT have the property (0*7+1=1 is squarefree) -/
example : tripleHasProperty 7 32 0 = false := by native_decide

/-- Test: {7, 32, 1} does NOT have the property -/
example : tripleHasProperty 7 32 1 = false := by native_decide

/-- Test: {7, 32, 18} - both 7 and 18 are "good" residues mod 25.
    7*18+1 = 127 (prime, squarefree), so this should fail -/
example : tripleHasProperty 7 32 18 = false := by native_decide

/-- Test: {7, 18, 43} - all are ≡ ±7 mod 25, but 7*18+1 = 127 is squarefree -/
example : tripleHasProperty 7 18 43 = false := by native_decide

/-!
## The Full Check

We need to verify: ∀ a b c < 50, a < b < c → tripleHasProperty a b c = false

This is C(50,3) = 19,600 checks.
-/

/-- Decidable predicate for finite check -/
def noTripleWorksIn (N : ℕ) : Prop :=
  ∀ a b c : Fin N, a.val < b.val → b.val < c.val →
    tripleHasProperty a.val b.val c.val = false

instance (N : ℕ) : Decidable (noTripleWorksIn N) := by
  unfold noTripleWorksIn
  infer_instance

/-- The key finite verification: No 3-element subset of {0,...,49} has the property.

    WARNING: This may take a while to compute. -/
theorem no_triple_works_50 : noTripleWorksIn 50 := by
  native_decide

end Erdos.Problem848.BruteForce
