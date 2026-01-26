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
  sorry

/-- The candidate set A₇ satisfies the non-squarefree product property. -/
theorem A₇_has_property (N : ℕ) : NonSquarefreeProductProp (A₇ N) := by
  sorry

/-- Sawhney's theorem: For large N, optimal sets are contained in A₇ or A₁₈. -/
theorem sawhney_main (c : ℝ) (hc : c > 0) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, ∀ A : Finset ℕ,
      A ⊆ Finset.range N →
      NonSquarefreeProductProp A →
      (A.card : ℝ) ≥ (1/25 - c) * N →
      (A ⊆ A₇ N ∨ A ⊆ A₁₈ N) := by
  sorry

/-- The main conjecture: A₇ (or A₁₈) achieves the maximum. -/
theorem problem_848 (N : ℕ) :
    ∀ A : Finset ℕ, A ⊆ Finset.range N → NonSquarefreeProductProp A →
      A.card ≤ (A₇ N).card := by
  sorry

end Erdos.Problem848
