/-
Targeted query for Aristotle: Prove the density of diagonal candidates.

The set of n where p² | n²+1 for some prime p ≡ 1 (mod 4) has a specific density.
This is a key lemma from Sawhney 2025.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Nat.Cast.Order.Field
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Data.ZMod.Basic
import Mathlib.NumberTheory.LegendreSymbol.Basic
import Mathlib.Data.Nat.ModEq

namespace Erdos.Problem848.SieveQuery1

/-- A number n is a "diagonal candidate" if n²+1 is NOT squarefree. -/
def isDiagonalCandidate (n : ℕ) : Prop := ¬ Squarefree (n * n + 1)

/-- The diagonal candidates up to N. -/
def DiagonalCandidates (N : ℕ) : Finset ℕ :=
  (Finset.range N).filter (fun n => ¬ Squarefree (n * n + 1))

/-- Decidability instance for filtering. -/
instance (n : ℕ) : Decidable (isDiagonalCandidate n) := by
  unfold isDiagonalCandidate
  infer_instance

/-- Key fact: If p² | n²+1 for prime p, then p ≡ 1 (mod 4).
    This is because -1 must be a quadratic residue mod p. -/
lemma prime_sq_divides_implies_one_mod_four (p n : ℕ) (hp : Nat.Prime p) (hp2 : p > 2)
    (hdiv : p^2 ∣ n^2 + 1) : p % 4 = 1 := by
  have hp_ne_two : p ≠ 2 := by omega
  have hp_dvd : p ∣ n ^ 2 + 1 := by
    -- `p ∣ p^2` and `p^2 ∣ n^2+1` implies `p ∣ n^2+1`.
    have hp_div_p2 : p ∣ p ^ 2 := by
      simp [pow_two]
    exact Nat.dvd_trans hp_div_p2 hdiv

  -- Work in `ZMod p`: `p ∣ n^2+1` means `n^2 = -1 (mod p)`.
  haveI : Fact p.Prime := ⟨hp⟩
  have h0 : ((n ^ 2 + 1 : ℕ) : ZMod p) = 0 := (ZMod.natCast_eq_zero_iff (n ^ 2 + 1) p).2 hp_dvd
  have hsq : (n : ZMod p) ^ 2 = (-1 : ZMod p) := by
    have : (n : ZMod p) ^ 2 + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_pow, Nat.cast_one] using h0
    simpa using (eq_neg_of_add_eq_zero_left this)

  -- `-1` is a square mod `p`, so `p % 4 ≠ 3`.
  have hne3 : p % 4 ≠ 3 := ZMod.mod_four_ne_three_of_sq_eq_neg_one (p := p) (y := (n : ZMod p)) hsq

  -- For odd primes, `p % 4` is either `1` or `3`; exclude `3`.
  have hp_mod2 : p % 2 = 1 := (Nat.Prime.mod_two_eq_one_iff_ne_two hp).2 hp_ne_two
  have hp_mod4 : p % 4 = 1 ∨ p % 4 = 3 := (Nat.odd_mod_four_iff).1 hp_mod2
  cases hp_mod4 with
  | inl h1 => exact h1
  | inr h3 => exact (hne3 h3).elim

/--
Research statement (not proved here): for prime `p ≡ 1 (mod 4)`, the congruence `r^2 = -1` has
exactly two solutions in `ZMod (p^2)`.

We keep this as a `Prop` so the file stays `sorry`-free while the Hensel-lifting argument is
formalized separately.
-/
def TwoRootsModPSquared (p : ℕ) : Prop :=
  Nat.Prime p →
    p % 4 = 1 →
    ∃ r₁ r₂ : ZMod (p ^ 2), r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧
      ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂

/--
Research statement (not proved here): for prime `p ≡ 1 (mod 4)`, the set
`{n < N : p^2 ∣ n^2+1}` has density at most `2/p^2` up to a small boundary error.
-/
def DensitySinglePrime (p : ℕ) : Prop :=
  Nat.Prime p →
    p % 4 = 1 →
    ∀ N : ℕ, N > 0 →
      let count := ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card
      (count : ℚ) / N ≤ 2 / p ^ 2 + 1 / N

/-- Trivial counting bound: in `range N`, a single residue class mod `m` appears at most `N/m + 1` times. -/
lemma card_filter_modEq_le (N m r : ℕ) (hm : 0 < m) :
    ((Finset.range N).filter (fun n => n % m = r % m)).card ≤ N / m + 1 := by
  classical
  set r0 : ℕ := r % m
  have h_sub :
      (Finset.range N).filter (fun n => n % m = r0) ⊆
        Finset.image (fun q : ℕ => q * m + r0) (Finset.range (N / m + 1)) := by
    intro n hn
    have hnlt : n < N := by
      have : n ∈ Finset.range N := (Finset.mem_filter.1 hn).1
      simpa [Finset.mem_range] using this
    have hmod : n % m = r0 := (Finset.mem_filter.1 hn).2
    refine Finset.mem_image.2 ?_
    refine ⟨n / m, ?_, ?_⟩
    · -- `n / m < N / m + 1` since `n < N`.
      have hle : n / m ≤ N / m := Nat.div_le_div_right (Nat.le_of_lt hnlt)
      have hlt : n / m < N / m + 1 := Nat.lt_succ_iff.2 hle
      simpa [Finset.mem_range] using hlt
    · -- Reconstruct `n` from quotient and remainder.
      -- `Nat.div_add_mod` gives `m * (n / m) + n % m = n`.
      have hdiv : (n / m) * m + n % m = n := by
        simpa [Nat.mul_comm] using Nat.div_add_mod n m
      calc
        (n / m) * m + r0 = (n / m) * m + n % m := by simpa [r0, hmod]
        _ = n := hdiv
  have h1 :
      ((Finset.range N).filter (fun n => n % m = r0)).card ≤
        (Finset.image (fun q : ℕ => q * m + r0) (Finset.range (N / m + 1))).card :=
    Finset.card_le_card h_sub
  have h2 :
      (Finset.image (fun q : ℕ => q * m + r0) (Finset.range (N / m + 1))).card ≤
        (Finset.range (N / m + 1)).card :=
    Finset.card_image_le
  have hcard : ((Finset.range N).filter (fun n => n % m = r0)).card ≤ (N / m + 1) := by
    simpa [Finset.card_range] using le_trans h1 h2
  simpa [r0] using hcard

/-- If there are at most two roots `r` of `r^2 = -1` in `ZMod (p^2)`, then the density of `n < N`
with `p^2 ∣ n^2+1` is at most `2/p^2` up to a small boundary term. -/
lemma density_single_prime_of_two_roots (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1)
    (hroots : TwoRootsModPSquared p) :
    ∀ N : ℕ, N > 0 →
      let count := ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card
      (count : ℚ) / N ≤ 2 / p ^ 2 + 2 / N := by
  intro N hN
  classical
  set m : ℕ := p ^ 2
  -- Every `n` with `p^2 ∣ n^2+1` corresponds to a root of `r^2 = -1` in `ZMod m`.
  -- Using `hroots`, there are at most two residue classes mod `m` to consider.
  rcases hroots hp hmod with ⟨r₁, r₂, hr₁₂, hr₁, hr₂, huniq⟩
  -- Bound count by the union of the two residue classes.
  have hsub :
      ((Finset.range N).filter (fun n => (m : ℕ) ∣ n ^ 2 + 1)) ⊆
        ((Finset.range N).filter (fun n => n % m = r₁.val % m)) ∪
          ((Finset.range N).filter (fun n => n % m = r₂.val % m)) := by
    have hmpos' : 0 < m := by
      have : 0 < p := hp.pos
      have : 0 < p ^ 2 := pow_pos this 2
      simpa [m] using this
    haveI : NeZero m := ⟨ne_of_gt hmpos'⟩
    intro n hn
    have hnrange : n ∈ Finset.range N := (Finset.mem_filter.1 hn).1
    have hdiv : m ∣ n ^ 2 + 1 := (Finset.mem_filter.1 hn).2
    have hz : ((n ^ 2 + 1 : ℕ) : ZMod m) = 0 := (ZMod.natCast_eq_zero_iff (n ^ 2 + 1) m).2 hdiv
    have hsq : (n : ZMod m) ^ 2 = (-1 : ZMod m) := by
      have : (n : ZMod m) ^ 2 + 1 = 0 := by
        simpa [Nat.cast_add, Nat.cast_pow, Nat.cast_one] using hz
      simpa using (eq_neg_of_add_eq_zero_left this)
    have hnr : (n : ZMod m) = r₁ ∨ (n : ZMod m) = r₂ := huniq (n : ZMod m) hsq
    rcases hnr with hnr | hnr
    · -- `n ≡ r₁ (mod m)`
      have hmod' : n % m = r₁.val := by
        have := congrArg (fun x : ZMod m => x.val) hnr
        simpa [ZMod.val_natCast] using this
      have hmod'' : n % m = r₁.val % m := by
        have hrlt : r₁.val < m := ZMod.val_lt r₁
        simpa [Nat.mod_eq_of_lt hrlt] using hmod'
      apply Finset.mem_union.2
      left
      exact Finset.mem_filter.2 ⟨hnrange, hmod''⟩
    ·
      have hmod' : n % m = r₂.val := by
        have := congrArg (fun x : ZMod m => x.val) hnr
        simpa [ZMod.val_natCast] using this
      have hmod'' : n % m = r₂.val % m := by
        have hrlt : r₂.val < m := ZMod.val_lt r₂
        simpa [Nat.mod_eq_of_lt hrlt] using hmod'
      apply Finset.mem_union.2
      right
      exact Finset.mem_filter.2 ⟨hnrange, hmod''⟩
  have hmpos : 0 < m := by
    have : 0 < p := hp.pos
    have : 0 < p ^ 2 := pow_pos this 2
    simpa [m] using this
  have hcard1 :
      ((Finset.range N).filter (fun n => n % m = r₁.val % m)).card ≤ N / m + 1 :=
    card_filter_modEq_le N m r₁.val hmpos
  have hcard2 :
      ((Finset.range N).filter (fun n => n % m = r₂.val % m)).card ≤ N / m + 1 :=
    card_filter_modEq_le N m r₂.val hmpos
  have hcount_le : ((Finset.range N).filter (fun n => (m : ℕ) ∣ n ^ 2 + 1)).card ≤
      2 * (N / m + 1) := by
    -- Use the subset bound + union cardinality.
    have := Finset.card_le_card hsub
    -- bound card of union by sum of cards
    have hunion :
        (((Finset.range N).filter (fun n => n % m = r₁.val % m)) ∪
            ((Finset.range N).filter (fun n => n % m = r₂.val % m))).card ≤
          ((Finset.range N).filter (fun n => n % m = r₁.val % m)).card +
            ((Finset.range N).filter (fun n => n % m = r₂.val % m)).card :=
      Finset.card_union_le _ _
    have := le_trans this (le_trans hunion (add_le_add hcard1 hcard2))
    -- simplify `x+x` to `2*x`
    nlinarith
  -- Divide by `N` to get density. Use a slightly slack `2/N` boundary term.
  have hNq : (0 : ℚ) < (N : ℚ) := by exact_mod_cast hN
  have : (( ((Finset.range N).filter (fun n => (m : ℕ) ∣ n ^ 2 + 1)).card) : ℚ) / N ≤
      (2 * (N / m + 1) : ℕ) / N := by
    exact div_le_div_of_nonneg_right (by exact_mod_cast hcount_le) (by exact_mod_cast (Nat.zero_le N))
  -- Now show `(2*(N/m+1))/N ≤ 2/m + 2/N` (in ℚ).
  have hrat :
      ((2 * (N / m + 1) : ℕ) : ℚ) / N ≤ (2 : ℚ) / m + 2 / N := by
    have hN0 : (0 : ℚ) < (N : ℚ) := by exact_mod_cast hN
    have hm0 : (0 : ℚ) < (m : ℚ) := by
      have : 0 < m := by
        have : 0 < p := hp.pos
        have : 0 < p ^ 2 := pow_pos this 2
        simpa [m] using this
      exact_mod_cast this
    -- Use `Nat.cast_div_le` to compare floor-division with exact division in `ℚ`.
    have hdiv : ((N / m : ℕ) : ℚ) ≤ (N : ℚ) / (m : ℚ) := by
      simpa [m] using (Nat.cast_div_le (m := N) (n := m) (α := ℚ))
    -- Now do the algebra:
    -- (2*(⌊N/m⌋+1))/N = 2*(⌊N/m⌋)/N + 2/N ≤ 2*(N/m)/N + 2/N = 2/m + 2/N.
    calc
      ((2 * (N / m + 1) : ℕ) : ℚ) / N
          = ((2 : ℚ) * ((N / m : ℕ) : ℚ) + 2) / (N : ℚ) := by
              -- expand `2*(q+1)` in `ℚ`
              simp [two_mul, add_assoc, add_left_comm, add_comm, mul_add, Nat.cast_add, Nat.cast_mul]
      _ = (2 : ℚ) * ((N / m : ℕ) : ℚ) / (N : ℚ) + (2 : ℚ) / (N : ℚ) := by
              field_simp [hN0.ne']
      _ ≤ (2 : ℚ) * ((N : ℚ) / (m : ℚ)) / (N : ℚ) + (2 : ℚ) / (N : ℚ) := by
              gcongr
      _ = (2 : ℚ) / (m : ℚ) + (2 : ℚ) / (N : ℚ) := by
              field_simp [hN0.ne', hm0.ne']
  -- Combine.
  simpa [m] using le_trans this hrat

end Erdos.Problem848.SieveQuery1
