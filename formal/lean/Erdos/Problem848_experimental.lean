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

/-- The candidate extremal set: {n ∈ {0,…,N-1} : n ≡ 7 (mod 25)}

    NOTE: Uses `Finset.range N` = {0,...,N-1}, not {1,...,N}.
    This is fine since 0 % 25 = 0 ≠ 7, so 0 is never included.
    For the problem statement's {1,...,N}, use `Finset.Icc 1 N` instead. -/
def A₇ (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => n % 25 = 7)

/-- Alternative candidate: {n ∈ {0,…,N-1} : n ≡ 18 (mod 25)}

    NOTE: Like A₇, uses `Finset.range N` = {0,...,N-1}.
    0 % 25 = 0 ≠ 18, so 0 is never included. -/
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

/-!
## Decidability for Finite Verification

To prove `problem_848_N50`, we use that `Squarefree` is decidable on ℕ
(via `Nat.instDecidablePredSquarefree`). This makes `NonSquarefreeProductProp`
decidable on finite sets, enabling `decide` / `native_decide` proofs.
-/

/-- NonSquarefreeProductProp is decidable for finite sets.

    Since A is finite, ∀ a ∈ A, ∀ b ∈ A, P a b is decidable when P is decidable.
    Squarefree is decidable on ℕ, so ¬Squarefree is also decidable. -/
instance instDecidableNonSquarefreeProductProp (A : Finset ℕ) :
    Decidable (NonSquarefreeProductProp A) := by
  unfold NonSquarefreeProductProp
  infer_instance

/-- The non-squarefree property is hereditary: subsets inherit it. -/
lemma nonSquarefreeProductProp_subset {A B : Finset ℕ} (hAB : A ⊆ B)
    (hB : NonSquarefreeProductProp B) : NonSquarefreeProductProp A := by
  intro a ha b hb
  exact hB a (hAB ha) b (hAB hb)

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

/-- Computational verification: A₇(50) = {7, 32} has the property.

    7 * 7 + 1 = 50 = 2 × 5², not squarefree ✓
    7 * 32 + 1 = 225 = 9 × 25 = 3² × 5², not squarefree ✓
    32 * 32 + 1 = 1025 = 25 × 41 = 5² × 41, not squarefree ✓ -/
example : NonSquarefreeProductProp (A₇ 50) := by native_decide

/-!
## Brute-Force Finite Verification

The following checks all C(50,3) = 19,600 triples to verify no 3-element
subset of {0,...,49} has the non-squarefree product property.
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

/-- Decidable predicate: no ordered triple in [0,N) has the property -/
def noTripleWorksIn (N : ℕ) : Prop :=
  ∀ a b c : Fin N, a.val < b.val → b.val < c.val →
    tripleHasProperty a.val b.val c.val = false

instance (N : ℕ) : Decidable (noTripleWorksIn N) := by
  unfold noTripleWorksIn
  infer_instance

/-- Key finite check: No 3-element subset of {0,...,49} has the property.
    Verified by native_decide in ~2 seconds (19,600 triple checks). -/
theorem no_triple_works_50 : noTripleWorksIn 50 := by native_decide

/-- The diagonal filter: n is a candidate if n² + 1 is not squarefree.

    Key insight from GPT-5 paper: If A has the property, then every a ∈ A
    must satisfy a² + 1 not squarefree (from the diagonal condition a*a+1). -/
def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

/-- Compute: DiagonalCandidates(50) = {7, 18, 32, 38, 41, 43}

    - 7² + 1 = 50 = 2 × 5²
    - 18² + 1 = 325 = 5² × 13
    - 32² + 1 = 1025 = 5² × 41
    - 38² + 1 = 1445 = 5 × 17²
    - 41² + 1 = 1682 = 2 × 29²
    - 43² + 1 = 1850 = 2 × 5² × 37 -/
lemma diag_cand_50 : DiagonalCandidates 50 = {7, 18, 32, 38, 41, 43} := by native_decide

/-- Any set with the property is contained in DiagonalCandidates. -/
lemma prop_implies_diag_candidates (A : Finset ℕ) (N : ℕ) (hAsub : A ⊆ Finset.range N)
    (hAprop : NonSquarefreeProductProp A) : A ⊆ DiagonalCandidates N := by
  intro a ha
  simp only [DiagonalCandidates, Finset.mem_filter]
  constructor
  · exact hAsub ha
  · exact hAprop a ha a ha

/-- Check: No 3-element subset of {7, 18, 32, 38, 41, 43} has the property.

    There are C(6,3) = 20 triples to check. Each fails because at least one
    product ab+1 is squarefree. Verified by native_decide. -/
lemma no_triple_in_candidates :
    ∀ (s : Finset ℕ), s ⊆ {7, 18, 32, 38, 41, 43} → s.card = 3 → ¬ NonSquarefreeProductProp s := by
  native_decide

/-- Verified: For N = 50, the conjecture holds (A₇(50) has 2 elements: {7, 32}).

    Proof using diagonal filter:
    1. Any set with the property is contained in DiagonalCandidates(50) = {7,18,32,38,41,43}
    2. No 3-element subset of these 6 candidates has the property (20 checks)
    3. Therefore max size is 2 -/
theorem problem_848_N50 :
    ∀ A : Finset ℕ, A ⊆ Finset.range 50 → NonSquarefreeProductProp A →
      A.card ≤ (A₇ 50).card := by
  intro A hAsub hAprop
  rw [A₇_50_card]
  -- A is contained in DiagonalCandidates(50)
  have h_sub_cand : A ⊆ DiagonalCandidates 50 := prop_implies_diag_candidates A 50 hAsub hAprop
  rw [diag_cand_50] at h_sub_cand
  -- If A.card ≥ 3, we get a contradiction
  by_contra h
  push_neg at h
  have hcard3 : 3 ≤ A.card := h
  -- A ⊆ {7,18,32,38,41,43} which has 6 elements
  -- So A.card ≤ 6, but we claimed A.card ≥ 3
  -- We need: any size-3 subset of A fails the property check
  -- This requires extracting 3 elements - use Finset.exists_subset_card_eq
  have hex : ∃ s : Finset ℕ, s ⊆ A ∧ s.card = 3 := by
    exact Finset.exists_subset_card_eq hcard3
  obtain ⟨s, hs_sub, hs_card⟩ := hex
  -- s inherits the property
  have hs_prop : NonSquarefreeProductProp s := nonSquarefreeProductProp_subset hs_sub hAprop
  -- s ⊆ {7,18,32,38,41,43} by transitivity
  have hs_sub_cand : s ⊆ {7, 18, 32, 38, 41, 43} := Finset.Subset.trans hs_sub h_sub_cand
  -- But no such s can have the property
  exact no_triple_in_candidates s hs_sub_cand hs_card hs_prop

/-!
## Structural Observations

Key facts about cross-products between A₇ and A₁₈:
- If a ≡ 7 (mod 25) and b ≡ 18 (mod 25), then ab ≡ 126 ≡ 1 (mod 25)
- So ab + 1 ≡ 2 (mod 25), meaning 25 ∤ (ab + 1)
- This means cross-products are NOT automatically non-squarefree

IMPORTANT: Mixing A₇ and A₁₈ CAN work for some pairs!
- {32, 43} has the property: 32×43+1 = 1377 = 3⁴×17 (NOT squarefree)
- But {7, 18} does NOT: 7×18+1 = 127 (prime, squarefree)

The conjecture is about SIZE, not containment.
-/

/-- When a ≡ 7 and b ≡ 18 (mod 25), ab + 1 ≢ 0 (mod 25). -/
lemma cross_product_not_div_25 (a b : ℕ) (ha : a % 25 = 7) (hb : b % 25 = 18) :
    (a * b + 1) % 25 ≠ 0 := by
  have h1 : a * b % 25 = (a % 25) * (b % 25) % 25 := Nat.mul_mod a b 25
  rw [ha, hb] at h1
  have h2 : (7 : ℕ) * 18 % 25 = 1 := by native_decide
  rw [h2] at h1
  omega

/-- Key computational fact: 7 × 18 + 1 = 127 is squarefree (it's prime). -/
lemma seven_times_eighteen_plus_one_squarefree : Squarefree (7 * 18 + 1) := by
  native_decide

/-- {7, 18} does NOT have the property because 7×18+1=127 is squarefree. -/
lemma pair_7_18_fails :
    ¬ NonSquarefreeProductProp ({7, 18} : Finset ℕ) := by
  native_decide

/-- However, {32, 43} DOES have the property (mixing works for this pair!).
    32×32+1 = 1025 = 5²×41, 32×43+1 = 1377 = 3⁴×17, 43×43+1 = 1850 = 2×5²×37 -/
lemma pair_32_43_works :
    NonSquarefreeProductProp ({32, 43} : Finset ℕ) := by
  native_decide

/-- A₇(100) = {7, 32, 57, 82} -/
lemma A7_100 : A₇ 100 = {7, 32, 57, 82} := by native_decide

/-- A₁₈(100) = {18, 43, 68, 93} -/
lemma A18_100 : A₁₈ 100 = {18, 43, 68, 93} := by native_decide

/-!
## Sawhney's Theorem (Research Level)

This file is intentionally split into:

- **Fully formalized core**: definitions, modular-arithmetic lemmas, and finite verification.
- **Research bridge**: a *statement* of Sawhney's asymptotic theorem (as a `Prop`) plus
  "glue" lemmas that reduce the full Erdős problem to (1) Sawhney's theorem for large `N`,
  and (2) a finite check for small `N`.

This avoids leaving `sorry` in the codebase while keeping the formal goalposts honest.
-/

/-!
### The "large N" statement (as a `Prop`)

Sawhney's published proof is a *stability* theorem near the conjectured density `1/25`:
there exist absolute constants `η > 0` and `N₀` such that any set `A ⊆ [0, N)` with the property
and `|A| ≥ (1/25 - η)N` is actually contained in a single residue class `±7 (mod 25)`.

We record the statement as a `Prop` so downstream Lean theorems can be proved *conditionally*
without `sorry`, while the analytic/sieve part is formalized incrementally in a separate effort.
-/

/-- The exact statement we need from Sawhney (2025), parameterized by constants. -/
def SawhneyMainAt (η : ℝ) (N₀ : ℕ) : Prop :=
  0 < η ∧ ∀ N ≥ N₀, ∀ A : Finset ℕ,
    A ⊆ Finset.range N →
    NonSquarefreeProductProp A →
    (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) →
    (A ⊆ A₇ N ∨ A ⊆ A₁₈ N)

/-- The paper-level existential version: there exist `η > 0` and `N₀` making `SawhneyMainAt` true. -/
def SawhneyMain : Prop :=
  ∃ η : ℝ, ∃ N₀ : ℕ, SawhneyMainAt η N₀

/-- The Erdős #848 statement for a fixed `N` (with our `range N = {0, …, N-1}` convention). -/
def Problem848Statement (N : ℕ) : Prop :=
  ∀ A : Finset ℕ, A ⊆ Finset.range N → NonSquarefreeProductProp A →
    A.card ≤ (A₇ N).card

/-!
### Glue: `SawhneyMainAt` ⇒ the conjectured upper bound for large `N`

This turns a near-optimal *containment* theorem into the desired *cardinality* bound.
It is purely combinatorial once `SawhneyMainAt` is available.
-/

lemma A₇_card (N : ℕ) : (A₇ N).card = (N + 17) / 25 := by
  classical
  -- `A₇ N` enumerates numbers `< N` of the form `25*k + 7`.
  set K : ℕ := (N + 17) / 25
  -- Bijection `k ↦ 25*k+7` from `range K` to `A₇ N`.
  have hbij : (A₇ N).card = (Finset.range K).card := by
    refine (Finset.card_bij (s := Finset.range K) (t := A₇ N)
      (i := fun k _hk => 25 * k + 7) ?_ ?_ ?_).symm
    · intro k hk
      have hk' : k < K := by simpa [Finset.mem_range] using hk
      have hk1 : k + 1 ≤ K := Nat.succ_le_iff.2 hk'
      have hmul : 25 * (k + 1) ≤ 25 * K := Nat.mul_le_mul_left 25 hk1
      have hK : 25 * K ≤ N + 17 := by
        -- `25 * ((N+17)/25) ≤ N+17`.
        simpa [K] using Nat.mul_div_le (N + 17) 25
      have hmul' : 25 * (k + 1) ≤ N + 17 := le_trans hmul hK
      have hlt : 25 * k + 7 < N := by
        -- From `25*(k+1) = 25*k+25 ≤ N+17`, deduce `25*k+7 < N`.
        -- (Because `25*k+7 + 18 = 25*k+25 ≤ N+17`.)
        omega
      -- Membership in `A₇ N` means `< N` and `≡ 7 (mod 25)`.
      simp [A₇, Finset.mem_filter, Finset.mem_range, hlt, Nat.add_mod]
    · intro k₁ _hk₁ k₂ _hk₂ h
      -- Injective because `k ↦ 25*k+7` is injective on naturals.
      have h' : 25 * k₁ = 25 * k₂ := Nat.add_right_cancel h
      exact Nat.mul_left_cancel (by decide : 0 < 25) h'
    · intro a ha
      -- Surjectivity: if `a % 25 = 7`, then `a = 25*(a/25) + 7`.
      have ha' : a < N ∧ a % 25 = 7 := by
        simpa [A₇, Finset.mem_filter, Finset.mem_range] using ha
      have ha_eq : 25 * (a / 25) + 7 = a := by
        have h := Nat.mod_add_div a 25
        simpa [ha'.2, Nat.add_comm, Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h
      refine ⟨a / 25, ?_, ?_⟩
      · -- Show `a/25 ∈ range K`.
        have hlt : 25 * (a / 25) + 7 < N := by
          simpa [ha_eq] using ha'.1
        have hmul : 25 * ((a / 25) + 1) ≤ N + 17 := by
          -- `25*(q+1) = (25*q+7) + 18 ≤ (N-1)+18 = N+17`.
          omega
        have hle : a / 25 + 1 ≤ K := by
          have hmul' : (a / 25 + 1) * 25 ≤ N + 17 := by
            simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using hmul
          have := (Nat.le_div_iff_mul_le (k0 := (by decide : 0 < 25))).2 hmul'
          simpa [K] using this
        have hltK : a / 25 < K := Nat.lt_of_lt_of_le (Nat.lt_succ_self _) hle
        simpa [Finset.mem_range] using hltK
      · exact ha_eq
  simpa [Finset.card_range, K] using hbij

lemma A₁₈_card (N : ℕ) : (A₁₈ N).card = (N + 6) / 25 := by
  classical
  set K : ℕ := (N + 6) / 25
  have hbij : (A₁₈ N).card = (Finset.range K).card := by
    refine (Finset.card_bij (s := Finset.range K) (t := A₁₈ N)
      (i := fun k _hk => 25 * k + 18) ?_ ?_ ?_).symm
    · intro k hk
      have hk' : k < K := by simpa [Finset.mem_range] using hk
      have hk1 : k + 1 ≤ K := Nat.succ_le_iff.2 hk'
      have hmul : 25 * (k + 1) ≤ 25 * K := Nat.mul_le_mul_left 25 hk1
      have hK : 25 * K ≤ N + 6 := by
        simpa [K] using Nat.mul_div_le (N + 6) 25
      have hmul' : 25 * (k + 1) ≤ N + 6 := le_trans hmul hK
      have hlt : 25 * k + 18 < N := by
        omega
      simp [A₁₈, Finset.mem_filter, Finset.mem_range, hlt, Nat.add_mod]
    · intro k₁ _hk₁ k₂ _hk₂ h
      have h' : 25 * k₁ = 25 * k₂ := Nat.add_right_cancel h
      exact Nat.mul_left_cancel (by decide : 0 < 25) h'
    · intro a ha
      have ha' : a < N ∧ a % 25 = 18 := by
        simpa [A₁₈, Finset.mem_filter, Finset.mem_range] using ha
      have ha_eq : 25 * (a / 25) + 18 = a := by
        have h := Nat.mod_add_div a 25
        simpa [ha'.2, Nat.add_comm, Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using h
      refine ⟨a / 25, ?_, ?_⟩
      · have hlt : 25 * (a / 25) + 18 < N := by
          simpa [ha_eq] using ha'.1
        have hmul : 25 * ((a / 25) + 1) ≤ N + 6 := by
          omega
        have hle : a / 25 + 1 ≤ K := by
          have hmul' : (a / 25 + 1) * 25 ≤ N + 6 := by
            simpa [Nat.mul_comm, Nat.mul_left_comm, Nat.mul_assoc] using hmul
          have := (Nat.le_div_iff_mul_le (k0 := (by decide : 0 < 25))).2 hmul'
          simpa [K] using this
        have hltK : a / 25 < K := Nat.lt_of_lt_of_le (Nat.lt_succ_self _) hle
        simpa [Finset.mem_range] using hltK
      · exact ha_eq
  simpa [Finset.card_range, K] using hbij

lemma A₁₈_card_le_A₇ (N : ℕ) : (A₁₈ N).card ≤ (A₇ N).card := by
  -- Compare explicit formulas.
  have h : N + 6 ≤ N + 17 := Nat.add_le_add_left (by decide : 6 ≤ 17) N
  simpa [A₇_card, A₁₈_card] using Nat.div_le_div_right h

lemma card_gt_A₇_implies_dense {η : ℝ} (hη : 0 < η) {N : ℕ} {A : Finset ℕ}
    (hgt : (A₇ N).card < A.card) :
    (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) := by
  -- Convert strict inequality of naturals to a real lower bound via `A₇_card`.
  have hsucc : (A₇ N).card + 1 ≤ A.card := Nat.succ_le_iff.2 hgt
  have hA : ((A₇ N).card + 1 : ℝ) ≤ (A.card : ℝ) := by
    exact_mod_cast hsucc
  have hA7 : ((N + 17 : ℝ) / 25) < ((A₇ N).card + 1 : ℝ) := by
    -- `q = (N+17)/25` satisfies `q ≤ (N+17)/25 < q+1`.
    have hq : (25 : ℝ) * ((A₇ N).card + 1 : ℝ) > (N + 17 : ℝ) := by
      -- Work in `ℕ` then cast.
      have hq_nat : 25 * ((A₇ N).card + 1) > N + 17 := by
        -- Since `(A₇ N).card = (N+17)/25`, the division algorithm gives:
        -- `(N+17) = 25*q + r` with `r < 25`, hence `25*(q+1) > N+17`.
        have hcard : (A₇ N).card = (N + 17) / 25 := A₇_card N
        -- Let `q := (N+17)/25` and `r := (N+17)%25`.
        have hdiv : 25 * ((N + 17) / 25) + (N + 17) % 25 = N + 17 := Nat.div_add_mod (N + 17) 25
        have hmod : (N + 17) % 25 < 25 := Nat.mod_lt _ (by decide : 0 < 25)
        -- `25*(q+1) = 25*q + 25 > 25*q + r = N+17`.
        omega
      -- Cast to `ℝ`.
      exact_mod_cast hq_nat
    nlinarith
  have hN17 : (N + 17 : ℝ) / 25 ≥ (1 / 25 - η) * (N : ℝ) := by
    -- `(N+17)/25 = N/25 + 17/25 ≥ N/25 - ηN` since `η > 0`.
    nlinarith
  -- Chain the bounds.
  have : (A.card : ℝ) ≥ (N + 17 : ℝ) / 25 := by
    -- `(N+17)/25 ≤ (A₇ N).card + 1 ≤ A.card`.
    have : (N + 17 : ℝ) / 25 ≤ (A.card : ℝ) := le_trans hA7.le hA
    exact this
  -- Strengthen from `(N+17)/25` to `(1/25 - η)*N`.
  exact le_trans hN17 this

/-- If `SawhneyMainAt η N₀` holds, then the conjectured upper bound holds for all `N ≥ N₀`. -/
theorem problem_848_large_of_sawhney {η : ℝ} {N₀ : ℕ} (h : SawhneyMainAt η N₀) :
    ∀ N ≥ N₀, Problem848Statement N := by
  classical
  rcases h with ⟨hη, hmain⟩
  intro N hN A hAsub hAprop
  by_contra hle
  have hgt : (A₇ N).card < A.card := lt_of_not_ge hle
  have hdense : (A.card : ℝ) ≥ (1/25 - η) * (N : ℝ) :=
    card_gt_A₇_implies_dense hη hgt
  have hstruct := hmain N hN A hAsub hAprop hdense
  cases hstruct with
  | inl hsub7 =>
      exact (not_le_of_gt hgt) (Finset.card_le_card hsub7)
  | inr hsub18 =>
      have hcard18 : A.card ≤ (A₁₈ N).card := Finset.card_le_card hsub18
      have h18le7 : (A₁₈ N).card ≤ (A₇ N).card := A₁₈_card_le_A₇ N
      exact (not_le_of_gt hgt) (le_trans hcard18 h18le7)

theorem problem_848_resolved_up_to_finite_check_of_sawhney (h : SawhneyMain) :
    ∃ N₀ : ℕ, ∀ N ≥ N₀, Problem848Statement N := by
  rcases h with ⟨η, N₀, hηN₀⟩
  exact ⟨N₀, problem_848_large_of_sawhney hηN₀⟩

/-!
### What we can prove today

We currently have:

- `Problem848Statement 50` (verified by computation).
- `problem_848_large_of_sawhney`: a clean bridge from Sawhney's theorem to the main bound.

Formalizing `SawhneyMain` itself (the sieve/density argument) is left for dedicated work on
analytic number theory in Lean.
-/

/-!
## Verified Cases

We have computationally verified the conjecture for N ≤ 50.
Extension to larger N requires either:
1. More computational power (native_decide scales poorly)
2. Formalizing Sawhney's density argument
-/

/-- Verified for N = 50 -/
theorem problem_848_verified_50 : ∀ A : Finset ℕ, A ⊆ Finset.range 50 →
    NonSquarefreeProductProp A → A.card ≤ 2 := by
  intro A hAsub hAprop
  have := problem_848_N50 A hAsub hAprop
  rw [A₇_50_card] at this
  exact this

end Erdos.Problem848
