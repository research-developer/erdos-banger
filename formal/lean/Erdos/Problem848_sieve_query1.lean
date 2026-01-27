/-
Ported from `formal/lean/aristotle/Problem848_sieve_query1_aristotle.lean`
(Aristotle Harmonic output) to Mathlib v4.27.0.

Key lemmas:
- `two_roots_mod_p_squared`: for `p ≡ 1 (mod 4)`, exactly two solutions to `r^2 = -1` in `ZMod (p^2)`
- `density_single_prime`: density bound for `{n < N : p^2 ∣ n^2 + 1}`

Porting fixes:
- `card_filter_mod_eq_le`: witness type mismatch (Lean 4.27 expects `≤` after simp)
- `density_single_prime`: replaced a failing `grind` with explicit algebra
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
    (hdiv : p ^ 2 ∣ n ^ 2 + 1) : p % 4 = 1 := by
  have hp_ne_two : p ≠ 2 := by omega
  have hp_dvd : p ∣ n ^ 2 + 1 := by
    have hp_div_p2 : p ∣ p ^ 2 := by
      simpa [pow_two] using Nat.dvd_mul_right p p
    exact Nat.dvd_trans hp_div_p2 hdiv

  haveI : Fact p.Prime := ⟨hp⟩
  have h0 :
      ((n ^ 2 + 1 : ℕ) : ZMod p) = 0 :=
    (ZMod.natCast_eq_zero_iff (n ^ 2 + 1) p).2 hp_dvd
  have hsq : (n : ZMod p) ^ 2 = (-1 : ZMod p) := by
    have : (n : ZMod p) ^ 2 + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_pow, Nat.cast_one] using h0
    simpa using (eq_neg_of_add_eq_zero_left this)

  have hne3 : p % 4 ≠ 3 :=
    ZMod.mod_four_ne_three_of_sq_eq_neg_one (p := p) (y := (n : ZMod p)) hsq

  have hp_mod2 : p % 2 = 1 := (Nat.Prime.mod_two_eq_one_iff_ne_two hp).2 hp_ne_two
  have hp_mod4 : p % 4 = 1 ∨ p % 4 = 3 := (Nat.odd_mod_four_iff).1 hp_mod2
  cases hp_mod4 with
  | inl h1 => exact h1
  | inr h3 => exact (hne3 h3).elim

/-- For prime p ≡ 1 (mod 4), there are exactly 2 residue classes r mod p²
    such that r² ≡ -1 (mod p²). -/
lemma two_roots_mod_p_squared (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) :
    ∃ r₁ r₂ : ZMod (p ^ 2),
      r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧
        ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂ := by
  obtain ⟨r₁, hr₁⟩ : ∃ r₁ : ZMod (p ^ 2), r₁ ^ 2 = -1 := by
    have h_quad_res : ∃ x : ℕ, x ^ 2 ≡ -1 [ZMOD p ^ 2] := by
      have h_hensel : ∀ {p : ℕ}, Nat.Prime p → p % 4 = 1 → ∃ x : ℕ, x ^ 2 ≡ -1 [ZMOD p] := by
        intro p hp hmod
        haveI := Fact.mk hp
        norm_num [← ZMod.intCast_eq_intCast_iff]
        obtain ⟨x, hx⟩ := ZMod.exists_sq_eq_neg_one_iff (p := p)
        exact Exists.elim (hx (by rw [hmod]; decide)) fun x hx =>
          ⟨x.val, by simpa [sq, ← ZMod.intCast_eq_intCast_iff] using hx.symm⟩
      obtain ⟨x, hx⟩ := @h_hensel p hp hmod
      obtain ⟨k, hk⟩ : ∃ k : ℤ, x ^ 2 = k * p - 1 := by
        exact hx.symm.dvd.imp fun k hk => by linarith
      obtain ⟨y, hy⟩ : ∃ y : ℤ, 2 * x * y ≡ -k [ZMOD p] := by
        obtain ⟨y, hy⟩ : ∃ y : ℤ, 2 * x * y ≡ 1 [ZMOD p] := by
          have h_inv : Int.gcd (2 * x) p = 1 := by
            refine' Nat.coprime_comm.mp (hp.coprime_iff_not_dvd.mpr _)
            norm_num [Int.natAbs_mul, Nat.Prime.dvd_mul hp]
            exact
              ⟨Nat.not_dvd_of_pos_of_lt (by norm_num) (by
                    contrapose! hmod
                    interval_cases p <;> trivial),
                fun h => by
                  have :=
                    Int.modEq_zero_iff_dvd.mp
                      (hx.symm.trans
                        (Int.modEq_zero_iff_dvd.mpr <| dvd_pow (Int.natCast_dvd_natCast.mpr h) two_ne_zero))
                  norm_num at this
                  norm_cast at this
                  have := Nat.le_of_dvd (by norm_num) this
                  interval_cases p <;> trivial⟩
          exact?  -- Aristotle: proof search in old environment
        exact ⟨y * -k, by simpa [mul_assoc] using hy.mul_right (-k)⟩
      use Int.natAbs (x + y * p)
      rw [Int.modEq_iff_dvd] at *
      obtain ⟨z, hz⟩ := hy
      use z - y ^ 2
      cases abs_cases (x + y * p : ℤ) <;> push_cast [*] <;> nlinarith
    obtain ⟨x, hx⟩ := h_quad_res
    refine ⟨x, ?_⟩
    erw [← ZMod.intCast_eq_intCast_iff] at hx
    simpa using hx

  refine' ⟨r₁, -r₁, _, _, _, _⟩ <;> simp_all +decide [sq]
  · rw [eq_neg_iff_add_eq_zero]
    by_contra h_contra
    have h_r1_zero : r₁ = 0 := by
      have h_r1_zero : (2 : ℕ) * r₁.val ≡ 0 [MOD p ^ 2] := by
        simp_all +decide [← ZMod.natCast_eq_natCast_iff]
        grind
      have h_r1_zero : p ^ 2 ∣ r₁.val := by
        exact
          (Nat.Coprime.dvd_of_dvd_mul_left
              (show Nat.Coprime (p ^ 2) 2 from by
                exact
                  Nat.Coprime.pow_left 2 <|
                    hp.coprime_iff_not_dvd.mpr fun h => by
                      have := Nat.le_of_dvd (by decide) h
                      interval_cases p <;> trivial)
              <| Nat.dvd_of_mod_eq_zero h_r1_zero)
      haveI := Fact.mk hp
      rw [← ZMod.natCast_eq_zero_iff] at h_r1_zero
      aesop
    norm_num [h_r1_zero] at hr₁
    rcases p with (_ | _ | _ | p) <;> cases hr₁ <;> contradiction
  · have h_solutions : ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = -r₁ := by
      intro r hr
      have h_eq : (r - r₁) * (r + r₁) = 0 := by
        grind
      have h_coprime :
          Nat.gcd (p ^ 2) (r - r₁).val = 1 ∨ Nat.gcd (p ^ 2) (r + r₁).val = 1 := by
        have h_coprime : ¬(p ∣ (r - r₁).val ∧ p ∣ (r + r₁).val) := by
          haveI := Fact.mk hp
          simp_all +decide [← ZMod.natCast_eq_zero_iff]
          intro h
          haveI := Fact.mk hp
          simp_all +decide [sub_eq_iff_eq_add, add_eq_zero_iff_eq_neg]
          rw [eq_neg_iff_add_eq_zero]
          have := congr_arg (fun x : ZMod (p ^ 2) => x.val) hr₁
          norm_num [ZMod.val_add, ZMod.val_mul] at this ⊢
          replace this := congr_arg (· % p) this
          norm_num [Nat.add_mod, Nat.mul_mod, Nat.pow_mod] at this
          simp_all +decide [← sq, ← ZMod.natCast_eq_natCast_iff']
          intro H
          rw [← two_mul] at H
          replace H := congr_arg (fun x : ZMod p => x ^ 2) H
          simp_all +decide [mul_pow]
          rcases p with (_ | _ | _ | p) <;> cases H <;> contradiction
        simp_all +decide [Nat.Prime.coprime_iff_not_dvd]
        tauto
      have h_div : (p ^ 2 : ℕ) ∣ (r - r₁).val ∨ (p ^ 2 : ℕ) ∣ (r + r₁).val := by
        have h_div : (p ^ 2 : ℕ) ∣ ((r - r₁).val * (r + r₁).val) := by
          haveI := Fact.mk hp
          simp_all +decide [← ZMod.natCast_eq_zero_iff]
        cases h_coprime with
        | inl hc =>
            exact Or.inr (Nat.Coprime.dvd_of_dvd_mul_left hc h_div)
        | inr hc =>
            exact Or.inl (Nat.Coprime.dvd_of_dvd_mul_right hc h_div)
      haveI := Fact.mk hp
      simp_all +decide [← ZMod.natCast_eq_zero_iff, sub_eq_iff_eq_add, add_eq_zero_iff_eq_neg]
    simpa only [sq] using h_solutions

/- The density of integers n where p² | n²+1 is 2/p² for each prime p ≡ 1 (mod 4). -/
noncomputable section AristotleLemmas

/-
The number of integers less than N congruent to r mod m is at most N/m + 1.
-/
lemma card_filter_mod_eq_le (N m r : ℕ) (hm : m > 0) :
    ((Finset.range N).filter (fun n => n ≡ r [MOD m])).card ≤ N / m + 1 := by
  have h_set :
      Finset.filter (fun n => n ≡ r [MOD m]) (Finset.range N) ⊆
        Finset.image (fun q => q * m + (r % m)) (Finset.range (N / m + 1)) := by
    intro n hn
    simp_all +decide [Nat.ModEq]
    -- Lean 4.27: simp turns `q ∈ range (N/m+1)` into `q ≤ N/m`.
    exact ⟨n / m, Nat.div_le_div_right hn.1.le, by linarith [Nat.mod_add_div n m]⟩
  exact le_trans (Finset.card_le_card h_set) (Finset.card_image_le.trans (by norm_num))

/-
The number of integers less than N congruent to r1 or r2 mod m (where r1+r2=m) is at most 2N/m + 1.
-/
lemma card_filter_mod_pair_le (N m r1 r2 : ℕ) (hm : m > 0) (h_sum : r1 + r2 = m) (h_r1_pos : 0 < r1)
    (h_r2_pos : 0 < r2) (h_ne : r1 ≠ r2) :
    ((Finset.range N).filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m])).card ≤ (2 * N : ℚ) / m + 1 := by
  obtain ⟨q, s, hs⟩ : ∃ q s : ℕ, N = q * m + s ∧ s < m := by
    exact ⟨N / m, N % m, by rw [Nat.div_add_mod'], Nat.mod_lt _ hm⟩
  have h_count :
      ((Finset.filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m]) (Finset.range N)).card : ℚ) ≤
        2 * q + (if r1 < s then 1 else 0) + (if r2 < s then 1 else 0) := by
    have h_partition :
        Finset.filter (fun n => n ≡ r1 [MOD m] ∨ n ≡ r2 [MOD m]) (Finset.range N) ⊆
          Finset.biUnion (Finset.range q)
              (fun i =>
                Finset.image (fun j => i * m + j)
                  (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m))) ∪
            (if r1 < s then {q * m + r1} else ∅) ∪ (if r2 < s then {q * m + r2} else ∅) := by
      intro n hn
      simp_all +decide [Nat.ModEq]
      by_cases h_case : n < q * m
      · exact Or.inl
          ⟨n / m, Nat.div_lt_of_lt_mul <| by linarith, n % m,
            ⟨Nat.mod_lt _ hm, by
              simpa
                [Nat.mod_eq_of_lt (show r1 < m from by linarith),
                  Nat.mod_eq_of_lt (show r2 < m from by linarith)] using hn.2⟩,
            by linarith [Nat.mod_add_div n m]⟩
      · cases hn.2 <;> simp_all +decide [Nat.mod_eq_of_lt]
        · obtain ⟨k, hk⟩ : ∃ k, n = q * m + k ∧ k < s := by
            exact ⟨n - q * m, by rw [Nat.add_sub_cancel' h_case], by
              rw [tsub_lt_iff_left h_case]
              linarith⟩
          simp_all +decide [Nat.add_mod, Nat.mod_eq_of_lt]
          rw [Nat.mod_eq_of_lt, Nat.mod_eq_of_lt] at * <;> first | linarith | aesop
        · obtain ⟨r, hr⟩ : ∃ r, n = q * m + r ∧ r < s := by
            exact ⟨n - q * m, by rw [Nat.add_sub_cancel' h_case], by
              rw [tsub_lt_iff_left h_case]
              linarith⟩
          simp_all +decide [Nat.mod_eq_of_lt (by linarith : r1 < m), Nat.mod_eq_of_lt (by linarith : r2 < m)]
          split_ifs <;> simp_all +decide [Nat.mod_eq_of_lt]
          · exact Or.inr <| Or.inr <| by
              linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
          · linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
          · exact Or.inr (by linarith [Nat.mod_eq_of_lt (by linarith : r < m)])
          · linarith [Nat.mod_eq_of_lt (by linarith : r < m)]
    have h_biUnion_card :
        (Finset.biUnion (Finset.range q)
              (fun i =>
                Finset.image (fun j => i * m + j)
                  (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)))).card ≤
          q * (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card := by
      exact
        le_trans Finset.card_biUnion_le
          (by
            exact
              le_trans (Finset.sum_le_sum fun _ _ => Finset.card_image_le) (by norm_num))
    have h_filter_card :
        (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card ≤ 2 := by
      have h_filter_card :
          (Finset.filter (fun j => j ≡ r1 [MOD m] ∨ j ≡ r2 [MOD m]) (Finset.range m)).card ≤
            Finset.card ({r1 % m, r2 % m} : Finset ℕ) := by
        refine Finset.card_le_card ?_
        simp_all +decide [Finset.subset_iff, Nat.ModEq]
        exact fun x hx hx' =>
          Or.imp (fun hx'' => by rw [← hx'', Nat.mod_eq_of_lt hx])
            (fun hx'' => by rw [← hx'', Nat.mod_eq_of_lt hx]) hx'
      exact h_filter_card.trans (Finset.card_insert_le _ _) |> le_trans <| by norm_num
    refine' le_trans (Nat.cast_le.mpr (Finset.card_le_card h_partition)) _
    refine' le_trans (Nat.cast_le.mpr (Finset.card_union_le _ _)) _
    exact
      mod_cast
        le_trans (add_le_add (Finset.card_union_le _ _) le_rfl)
          (by
            split_ifs <;> norm_num <;> nlinarith)
  split_ifs at h_count <;> simp_all +decide [Nat.modEq_iff_dvd]
  ·
    rw [div_add_one, le_div_iff₀] <;> norm_cast at * <;>
      nlinarith only [hs, h_sum, h_count, ‹r1 < s›, ‹r2 < s›]
  ·
    exact
      le_trans h_count
        (by
          rw [div_add_one, le_div_iff₀] <;> norm_cast <;>
            nlinarith only [hs, h_sum, ‹r1 < s›, ‹s ≤ r2›])
  ·
    exact
      h_count.trans
        (by
          rw [div_add_one, le_div_iff₀] <;> norm_cast <;> nlinarith only [hs, hm])
  ·
    exact
      le_add_of_le_of_nonneg
        (by
          rw [le_div_iff₀ (by positivity)]
          nlinarith
            [(by norm_cast : (s : ℚ) ≤ r1), (by norm_cast : (s : ℚ) ≤ r2),
              (by norm_cast : (r1 : ℚ) + r2 = m)])
        zero_le_one

end AristotleLemmas

lemma density_single_prime (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) (N : ℕ) (hN : N > 0) :
    let count := ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card
    (count : ℚ) / N ≤ 2 / p ^ 2 + 1 / N := by
  classical
  obtain ⟨r₁, r₂, hr⟩ :
      ∃ r₁ r₂ : ZMod (p ^ 2),
        r₁ ≠ r₂ ∧ r₁ ^ 2 = -1 ∧ r₂ ^ 2 = -1 ∧ ∀ r : ZMod (p ^ 2), r ^ 2 = -1 → r = r₁ ∨ r = r₂ := by
    simpa using two_roots_mod_p_squared p hp hmod

  have h_set_eq :
      {n ∈ Finset.range N | p ^ 2 ∣ n ^ 2 + 1} =
        {n ∈ Finset.range N | n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2]} := by
    ext n
    simp_all +decide [← ZMod.natCast_eq_natCast_iff]
    intro hn
    haveI := Fact.mk hp
    simp_all +decide [← ZMod.natCast_eq_zero_iff]
    grind

  have h_card_filter :
      ((Finset.range N).filter (fun n => n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2])).card ≤
        (2 * N : ℚ) / p ^ 2 + 1 := by
    convert card_filter_mod_pair_le N (p ^ 2) r₁.val r₂.val _ _ _ _ _ using 1 <;> norm_num [Nat.ModEq]
    · exact pow_pos hp.pos 2
    ·
      have h_sum : r₁.val + r₂.val ≡ 0 [MOD p ^ 2] := by
        have h_card_filter : r₁ + r₂ = 0 := by
          have h_sum : r₁ + r₂ = 0 := by
            have h_neg : (-r₁) ^ 2 = -1 := by
              grind
            have h_char : (2 : ZMod (p ^ 2)) ≠ 0 := by
              intro h
              rcases p with (_ | _ | _ | p) <;> cases h <;> trivial
            grind
          exact h_sum
        simp_all +decide [← ZMod.natCast_eq_natCast_iff]
        cases p <;> aesop
      rw [Nat.modEq_zero_iff_dvd] at h_sum
      obtain ⟨k, hk⟩ := h_sum
      rcases k with (_ | _ | k) <;> simp_all +decide [Nat.pow_succ', mul_assoc]
      have h_contra : r₁.val < p ^ 2 ∧ r₂.val < p ^ 2 := by
        haveI := Fact.mk hp
        exact ⟨r₁.val_lt, r₂.val_lt⟩
      nlinarith only [hk, h_contra, hp.two_le]
    · grind
    · grind
    ·
      haveI := Fact.mk hp
      exact fun h => hr.1 <| by
        rw [← ZMod.natCast_zmod_val r₁, ← ZMod.natCast_zmod_val r₂, h]

  have hcard_eq :
      ((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card =
        ((Finset.range N).filter (fun n => n ≡ r₁.val [MOD p ^ 2] ∨ n ≡ r₂.val [MOD p ^ 2])).card := by
    simpa using congrArg Finset.card h_set_eq

  have hcount_le :
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) ≤ (2 * N : ℚ) / p ^ 2 + 1 := by
    simpa [hcard_eq] using h_card_filter

  have hdiv :
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) / N ≤
        ((2 * N : ℚ) / p ^ 2 + 1) / N := by
    exact div_le_div_of_nonneg_right hcount_le (by exact_mod_cast (Nat.zero_le N))

  have hN0 : (N : ℚ) ≠ 0 := by exact_mod_cast (Nat.ne_of_gt hN)

  have hrhs : ((2 * N : ℚ) / p ^ 2 + 1) / (N : ℚ) = (2 : ℚ) / p ^ 2 + 1 / (N : ℚ) := by
    calc
      ((2 * (N : ℚ)) / (p ^ 2 : ℚ) + 1) / (N : ℚ) =
          ((2 * (N : ℚ)) / (p ^ 2 : ℚ)) / (N : ℚ) + 1 / (N : ℚ) := by
            simpa [add_div]
      _ = (2 * (N : ℚ)) / ((p ^ 2 : ℚ) * (N : ℚ)) + 1 / (N : ℚ) := by
            simp [div_div]
      _ = (2 : ℚ) / (p ^ 2 : ℚ) + 1 / (N : ℚ) := by
            have :
                (2 * (N : ℚ)) / ((p ^ 2 : ℚ) * (N : ℚ)) = (2 : ℚ) / (p ^ 2 : ℚ) := by
              simpa [mul_assoc, mul_left_comm, mul_comm] using
                (mul_div_mul_right (a := (2 : ℚ)) (b := (p ^ 2 : ℚ)) (c := (N : ℚ)) hN0)
            simpa [this]

  have := (show
      (((Finset.range N).filter (fun n => (p ^ 2 : ℕ) ∣ n ^ 2 + 1)).card : ℚ) / N ≤
        (2 : ℚ) / p ^ 2 + 1 / N from by
      simpa [hrhs] using hdiv)
  simpa using this

end Erdos.Problem848.SieveQuery1
