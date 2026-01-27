/-
This file was edited by Aristotle.

Lean version: leanprover/lean4:v4.24.0
Mathlib version: f897ebcf72cd16f89ab4577d0c826cd14afaafc7
This project request had uuid: 09934619-efc0-46c7-8cc9-8114aea1db5e

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
  -- By contradiction, assume $A$ has more than 2 elements.
  by_contra h_contra;
  -- Since $A$ has more than 2 elements, it must contain at least 3 distinct elements from $\{1, 2, \ldots, 50\}$.
  obtain ⟨s, hs⟩ : ∃ s : Finset ℕ, s ⊆ Finset.range 50 ∧ s.card = 3 ∧ ∀ a ∈ s, ∀ b ∈ s, ¬Squarefree (a * b + 1) := by
    exact Exists.elim ( Finset.exists_subset_card_eq ( by linarith [ show ( Erdos.Problem848.A₇ 50 ).card = 2 by native_decide ] : 3 ≤ A.card ) ) fun s hs => ⟨ s, Finset.Subset.trans hs.1 hA, hs.2, fun a ha b hb => hA_prop a ( hs.1 ha ) b ( hs.1 hb ) ⟩;
  -- Let's enumerate all possible 3-element subsets of $\{1, 2, \ldots, 50\}$ and check if any of them satisfy the non-squarefree product property.
  have h_enum : ∀ s ∈ Finset.powersetCard 3 (Finset.range 50), ¬(∀ a ∈ s, ∀ b ∈ s, ¬Squarefree (a * b + 1)) := by
    native_decide;
  exact h_enum s ( Finset.mem_powersetCard.mpr ⟨ hs.1, hs.2.1 ⟩ ) hs.2.2

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
If a set of numbers mod 25 has the property that ab+1 is divisible by 25 for all pairs, then the set is contained in {7} or {18}.
-/
lemma nat_mod25_clique (S : Finset ℕ) (h_bound : ∀ x ∈ S, x < 25)
    (h_prod : ∀ x ∈ S, ∀ y ∈ S, (x * y + 1) % 25 = 0) :
    S ⊆ {7} ∨ S ⊆ {18} := by
      -- The solutions to x^2 ≡ -1 (mod 25) are x ≡ 7 or 18 (mod 25).
      have h_solutions : ∀ x ∈ S, x % 25 = 7 ∨ x % 25 = 18 := by
        intro x hx; specialize h_prod x hx x hx; rcases h_bound x hx with ( _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | _ | x ) <;> simp_all +arith +decide;
      by_contra h_contra;
      -- If S contains both 7 and 18, then 7*18 + 1 = 127 ≡ 2 (mod 25), which is not zero modulo 25.
      obtain ⟨x, hxS, hx⟩ : ∃ x ∈ S, x % 25 = 7 := by
        grind
      obtain ⟨y, hyS, hy⟩ : ∃ y ∈ S, y % 25 = 18 := by
        grind;
      exact absurd ( h_prod x hxS y hyS ) ( by norm_num [ Nat.add_mod, Nat.mul_mod, hx, hy ] )

/-
1682 is not squarefree.
-/
lemma not_squarefree_1682 : ¬ Squarefree 1682 := by
  native_decide +revert

/-
A_169 is the set of numbers less than N that are congruent to 70 modulo 169.
-/
def A_169 (N : ℕ) : Finset ℕ := (Finset.range N).filter (fun n => n % 169 = 70)

/-
The set A_169 has the non-squarefree product property.
-/
lemma A_169_prop (N : ℕ) : Erdos.Problem848.NonSquarefreeProductProp (A_169 N) := by
  -- Let's choose any $a, b \in A_{169}$.
  intro a ha b hb
  simp [A_169] at ha hb ⊢;
  -- Since $a \equiv 70 \pmod{169}$ and $b \equiv 70 \pmod{169}$, we have $ab \equiv 70 \cdot 70 \equiv 4900 \equiv -1 \pmod{169}$.
  have h_mod : (a * b + 1) % 169 = 0 := by
    norm_num [ Nat.add_mod, Nat.mul_mod, ha.2, hb.2 ];
  exact fun h => absurd ( h 13 ( by exact Nat.dvd_of_mod_eq_zero ( show ( a * b + 1 ) % 13 ^ 2 = 0 by exact Nat.mod_eq_zero_of_dvd <| dvd_trans ( by decide ) <| Nat.dvd_of_mod_eq_zero h_mod ) ) ) ( by decide )

/-
For N > 70, A_169 is not a subset of A_7 or A_18.
-/
lemma A_169_not_subset (N : ℕ) (hN : N > 70) : ¬ (A_169 N ⊆ Erdos.Problem848.A₇ N) ∧ ¬ (A_169 N ⊆ Erdos.Problem848.A₁₈ N) := by
  -- Since $70 \in A_{169}$ but $70 \notin A_7$ and $70 \notin A_{18}$, we have $A_{169} \not\subseteq A_7$ and $A_{169} \not\subseteq A_{18}$.
  have h70_not_in_A7 : 70 ∉ A₇ N := by
    exact fun h => by have := Finset.mem_filter.mp h; norm_num at this;
  have h70_not_in_A18 : 70 ∉ A₁₈ N := by
    exact fun h => by have := Finset.mem_filter.mp h; norm_num at this;
  exact ⟨ fun h => h70_not_in_A7 <| h <| Finset.mem_filter.mpr ⟨ Finset.mem_range.mpr hN, by norm_num ⟩, fun h => h70_not_in_A18 <| h <| Finset.mem_filter.mpr ⟨ Finset.mem_range.mpr hN, by norm_num ⟩ ⟩

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
  unfold Erdos.Problem848.NonSquarefreeProductProp;
  use 1;
  refine' ⟨ by norm_num, fun x => _ ⟩;
  refine' ⟨ x + 71, _, _ ⟩ <;> norm_num;
  refine' ⟨ { 70 }, _, _, _, _, _ ⟩ <;> norm_num;
  · native_decide +revert;
  · linarith;
  · exact fun h => by have := Finset.mem_filter.mp h; norm_num at this;
  · exact fun h => by have := Finset.mem_filter.mp h; norm_num at this;

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
