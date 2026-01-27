/-
This file was edited by Aristotle.

Lean version: leanprover/lean4:v4.24.0
Mathlib version: f897ebcf72cd16f89ab4577d0c826cd14afaafc7
This project request had uuid: 25e4c576-e915-46eb-9f31-b644967c8946

To cite Aristotle, tag @Aristotle-Harmonic on GitHub PRs/issues, and add as co-author to commits:
Co-authored-by: Aristotle (Harmonic) <aristotle-harmonic@harmonic.fun>

The following was proved by Aristotle:

- theorem problem_848_N50 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 50 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 50).card

The following was negated by Aristotle:

- theorem sawhney_main (c : ℝ) (hc : c > 0) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - c) * N →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N)

Here is the code for the `negate_state` tactic, used within these negations:

```lean
import Mathlib
open Lean Meta Elab Tactic in
elab "revert_all" : tactic => do
  let goals ← getGoals
  let mut newGoals : List MVarId := []
  for mvarId in goals do
    newGoals := newGoals.append [(← mvarId.revertAll)]
  setGoals newGoals

open Lean.Elab.Tactic in
macro "negate_state" : tactic => `(tactic|
  (
    guard_goal_nums 1
    revert_all
    refine @(((by admit) : ∀ {p : Prop}, ¬p → p) ?_)
    try (push_neg; guard_goal_nums 1)
  )
)
```
-/

/-
Problem 848: Erdős Problem #848 (Erdős-Sárközy)

Status: DECIDABLE (resolved up to finite check)
Tags: number theory, squarefree, extremal combinatorics

Statement:
Is the maximum size of a set A ⊆ {1,…,N} such that ab+1 is never squarefree
(for all a,b ∈ A) achieved by taking those n ≡ 7 (mod 25)?

Resolution (Sawhney 2025):
For sufficiently large N, if |A| ≥ (1/25 - c)N for some c > 0, then
A ⊆ {n : n ≡ 7 (mod 25)} or A ⊆ {n : n ≡ 18 (mod 25)}.
(Note: 18 ≡ -7 (mod 25), so these are n ≡ ±7 (mod 25).)

Remaining: Effectivize N_0 bound and verify finitely many cases.
-/

import Erdos.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.Data.Real.Basic


namespace Erdos.Problem848

/-!
# Problem 848: Erdős-Sárközy Squarefree Products Conjecture

## Mathematical Statement

Let A ⊆ {1,…,N}. We say A has the **non-squarefree product property** if
for all a, b ∈ A, the number ab + 1 is NOT squarefree (i.e., divisible by p²
for some prime p).

**Conjecture:** The maximum size of such a set A is achieved by
A₇ = {n ∈ {1,…,N} : n ≡ 7 (mod 25)} or equivalently
A₁₈ = {n ∈ {1,…,N} : n ≡ 18 (mod 25)}.

## Key Insight

If a ≡ b ≡ 7 (mod 25), then ab ≡ 49 ≡ -1 (mod 25), so ab + 1 ≡ 0 (mod 25).
Since 25 = 5², this means ab + 1 is divisible by 5², hence not squarefree.

## Status

- **Proved for large N** by Sawhney (2025) via density arguments
- **Decidable**: Finite verification needed for small N
- See: arXiv:2511.16072 (GPT-5 paper, Section IV.1)
-/

-- Problem metadata
def problem : ErdosProblem := {
  id := 848
  title := "Erdős-Sárközy Squarefree Products"
  status := "decidable"
}

/-- A set A has the non-squarefree product property if ab+1 is not squarefree
    for all a, b in A. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- The candidate extremal set: {n ∈ {1,…,N} : n ≡ 7 (mod 25)} -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- Alternative candidate: {n ∈ {1,…,N} : n ≡ 18 (mod 25)} -/
def A₁₈ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 18)

/-- Key lemma: If a ≡ b ≡ 7 (mod 25), then 5² | (ab + 1). -/
lemma mod25_divisibility (a b : ℕ) (ha : a % 25 = 7) (hb : b % 25 = 7) :
    25 ∣ (a * b + 1) := by
  -- a = 25k + 7, b = 25m + 7 for some k, m
  -- ab = (25k + 7)(25m + 7) = 625km + 175k + 175m + 49
  --    = 25(25km + 7k + 7m + 2) - 1
  -- So ab + 1 = 25(25km + 7k + 7m + 2)
  have h1 : a * b % 25 = (a % 25) * (b % 25) % 25 := Nat.mul_mod a b 25
  rw [ha, hb] at h1
  -- 7 * 7 = 49 = 25 + 24, so 49 % 25 = 24
  have h2 : (7 : ℕ) * 7 % 25 = 24 := by native_decide
  rw [h2] at h1
  -- ab % 25 = 24 means ab + 1 % 25 = 0
  have h3 : (a * b + 1) % 25 = 0 := by omega
  exact Nat.dvd_of_mod_eq_zero h3

/-- Helper: 25 = 5² -/
lemma twenty_five_eq_five_sq : (25 : ℕ) = 5 ^ 2 := by native_decide

/-- Helper: 5 is prime -/
lemma five_prime : Nat.Prime 5 := by native_decide

/-- If 25 | n and n > 0, then n is not squarefree (since 5² | n). -/
lemma not_squarefree_of_dvd_25 {n : ℕ} (_hn : n > 0) (h : 25 ∣ n) : ¬ Squarefree n := by
  intro hsq
  rw [twenty_five_eq_five_sq] at h
  have hunit : IsUnit (5 : ℕ) := hsq 5 h
  -- In ℕ, the only unit is 1. So IsUnit 5 means 5 = 1, contradiction.
  have : (5 : ℕ) = 1 := Nat.isUnit_iff.mp hunit
  omega

/-- The candidate set A₇ satisfies the non-squarefree product property. -/
theorem A₇_has_property (N : ℕ) : NonSquarefreeProductProp (A₇ N) := by
  intro a ha b hb
  -- a and b are in A₇, so a % 25 = 7 and b % 25 = 7
  simp only [A₇, Finset.mem_filter] at ha hb
  have ha_mod : a % 25 = 7 := ha.2
  have hb_mod : b % 25 = 7 := hb.2
  -- By mod25_divisibility, 25 | (ab + 1)
  have hdiv : 25 ∣ (a * b + 1) := mod25_divisibility a b ha_mod hb_mod
  -- ab + 1 > 0
  have hpos : a * b + 1 > 0 := Nat.succ_pos _
  -- Therefore ab + 1 is not squarefree
  exact not_squarefree_of_dvd_25 hpos hdiv

/-- The same holds for A₁₈ (n ≡ 18 mod 25 = -7 mod 25). -/
lemma mod25_divisibility_18 (a b : ℕ) (ha : a % 25 = 18) (hb : b % 25 = 18) :
    25 ∣ (a * b + 1) := by
  have h1 : a * b % 25 = (a % 25) * (b % 25) % 25 := Nat.mul_mod a b 25
  rw [ha, hb] at h1
  -- 18 * 18 = 324 = 12 * 25 + 24, so 324 % 25 = 24
  have h2 : (18 : ℕ) * 18 % 25 = 24 := by native_decide
  rw [h2] at h1
  have h3 : (a * b + 1) % 25 = 0 := by omega
  exact Nat.dvd_of_mod_eq_zero h3

/-- A₁₈ also satisfies the non-squarefree product property. -/
theorem A₁₈_has_property (N : ℕ) : NonSquarefreeProductProp (A₁₈ N) := by
  intro a ha b hb
  simp only [A₁₈, Finset.mem_filter] at ha hb
  have hdiv : 25 ∣ (a * b + 1) := mod25_divisibility_18 a b ha.2 hb.2
  have hpos : a * b + 1 > 0 := Nat.succ_pos _
  exact not_squarefree_of_dvd_25 hpos hdiv

/-- The size of A₇(N) is at most N (trivial upper bound). -/
lemma A₇_card_le_N (N : ℕ) : (A₇ N).card ≤ N := by
  simp only [A₇]
  have h1 : ((Finset.range N).filter (fun n => n % 25 = 7)).card ≤ (Finset.range N).card :=
    Finset.card_filter_le _ _
  have h2 : (Finset.range N).card = N := Finset.card_range N
  omega

/-- Compute: A₇(50) = {7, 32} -/
example : A₇ 50 = {7, 32} := by native_decide

/-- Compute: |A₇(50)| = 2 -/
lemma A₇_50_card : (A₇ 50).card = 2 := by native_decide

/-- Verified: For N = 50, the conjecture holds (A₇(50) has 2 elements: {7, 32}).
    NOTE: Full computational verification requires decidability of Squarefree
    which involves checking all prime divisors. This is left as sorry pending
    a Decidable instance for NonSquarefreeProductProp. -/
theorem problem_848_N50 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 50 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 50).card := by
  -- The full proof requires enumerating all 2^50 subsets and checking
  -- the squarefree condition. This is computationally intensive.
  -- A SAT/SMT approach would be more practical.
  intro A hA hA_prop;
  -- Since $A$ has the non-squarefree product property, for all $a, b \in A$, $ab + 1$ is divisible by a square of a prime.
  -- We will check all possible sets $A$ with $|A| > 2$ and show that they do not satisfy the property.
  have h_check : ∀ A ⊆ Finset.range 50, A.card > 2 → ¬NonSquarefreeProductProp A := by
    intro A hA hA_card hA_prop;
    -- Let's consider all possible sets $A$ with $|A| > 2$ and show that they do not satisfy the property.
    have h_check : ∀ A ∈ Finset.powersetCard 3 (Finset.range 50), ¬NonSquarefreeProductProp A := by
      unfold Erdos.Problem848.NonSquarefreeProductProp; native_decide;
    -- Since $A$ has more than 2 elements, we can choose a subset $B$ of $A$ with exactly 3 elements.
    obtain ⟨B, hB⟩ : ∃ B ⊆ A, B.card = 3 := by
      exact?;
    exact h_check B ( Finset.mem_powersetCard.mpr ⟨ Finset.Subset.trans hB.1 hA, hB.2 ⟩ ) ( fun a ha b hb => hA_prop a ( hB.1 ha ) b ( hB.1 hb ) );
  exact le_of_not_gt fun h => h_check A hA h hA_prop

/-!
## Sawhney's Theorem (Research Level)

The following theorem requires formalizing Sawhney's density argument from
arXiv:2511.16072. The proof uses:
1. Large sieve inequalities (Montgomery-Vaughan 1973)
2. Density increment arguments
3. Möbius function analysis

This is beyond simple tactic automation and requires careful formalization
of analytic number theory techniques.
-/

/- Aristotle found this block to be false. Here is a proof of the negation:

noncomputable section AristotleLemmas

/-
The set {70} satisfies the NonSquarefreeProductProp.
-/
lemma seventy_bad : Erdos.Problem848.NonSquarefreeProductProp {70} := by
  exact fun a ha b hb => by rw [ Finset.mem_singleton.mp ha, Finset.mem_singleton.mp hb ] ; native_decide;

/-
The set {70} is not a subset of A7(N) or A18(N) for N > 70, because 70 is 20 mod 25, not 7 or 18.
-/
lemma seventy_not_candidate (N : ℕ) (hN : N > 70) :
    ¬ ({70} ⊆ Erdos.Problem848.A₇ N ∨ {70} ⊆ Erdos.Problem848.A₁₈ N) := by
      unfold Erdos.Problem848.A₇ Erdos.Problem848.A₁₈; norm_num [ Finset.subset_iff ] ;

/-
The statement of Sawhney's theorem as provided is false for large c.
-/
theorem sawhney_main_false : ¬ (∀ c : ℝ, c > 0 →
    ∃ N₀ : ℕ, ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      Erdos.Problem848.NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - c) * N →
      (A ⊆ Erdos.Problem848.A₇ N ∨ A ⊆ Erdos.Problem848.A₁₈ N)) := by
  intro h
  specialize h 1 (by norm_num)
  rcases h with ⟨N₀, hN₀⟩
  let N := max N₀ 71
  have hN : N ≥ N₀ := le_max_left _ _
  have hN71 : N > 70 := by
    have : N ≥ 71 := le_max_right _ _
    linarith
  specialize hN₀ N hN {70}
  have h_subset : {70} ⊆ Finset.range N := by
    rw [Finset.singleton_subset_iff, Finset.mem_range]
    exact hN71
  have h_prop : Erdos.Problem848.NonSquarefreeProductProp {70} := seventy_bad
  have h_card : ({70} : Finset ℕ).card = 1 := Finset.card_singleton 70
  have h_dens : (({70} : Finset ℕ).card : ℝ) ≥ (1/25 - 1) * N := by
    rw [h_card]
    have : (1/25 - 1 : ℝ) = -0.96 := by norm_num
    rw [this]
    have : (N : ℝ) ≥ 0 := Nat.cast_nonneg N
    nlinarith
  specialize hN₀ h_subset h_prop h_dens
  have h_not := seventy_not_candidate N hN71
  contradiction

end AristotleLemmas

/-
Sawhney's theorem: For large N, optimal sets are contained in A₇ or A₁₈.
-/
theorem sawhney_main (c : ℝ) (hc : c > 0) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - c) * N →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N) := by
  -- Wait, there's a mistake. We can actually prove the opposite.
  negate_state;
  -- Proof starts here:
  -- By taking $c = 1$, we can apply the lemma sawhney_main_false to obtain the desired result.
  use 1; norm_num;
  intro x;
  refine' ⟨ 71 + x, _, { 70 }, _, _, _ ⟩ <;> norm_num;
  · -- Since $x$ is a natural number, we have $70 < 71 + x$.
    linarith;
  · exact?;
  · exact ⟨ by linarith, by unfold Erdos.Problem848.A₇; norm_num [ Nat.add_mod ], by unfold Erdos.Problem848.A₁₈; norm_num [ Nat.add_mod ] ⟩

-/
/-- Sawhney's theorem: For large N, optimal sets are contained in A₇ or A₁₈. -/
theorem sawhney_main (c : ℝ) (hc : c > 0) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - c) * N →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N) := by
  sorry

/- Aristotle failed to find a proof. -/
-- Requires Sawhney's density argument

/-- The main conjecture: A₇ (or A₁₈) achieves the maximum. -/
theorem problem_848 (N : ℕ) :
    ∀ A : Finset ℕ, A ⊆ Finset.range N → NonSquarefreeProductProp A →
      A.card ≤ (A₇ N).card := by
  sorry

end Erdos.Problem848
