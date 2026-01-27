/-
This file was edited by Aristotle.

Lean version: leanprover/lean4:v4.24.0
Mathlib version: f897ebcf72cd16f89ab4577d0c826cd14afaafc7
This project request had uuid: a1e71be2-0b59-4357-99e6-2c37618eb656

To cite Aristotle, tag @Aristotle-Harmonic on GitHub PRs/issues, and add as co-author to commits:
Co-authored-by: Aristotle (Harmonic) <aristotle-harmonic@harmonic.fun>

The following was negated by Aristotle:

- lemma squarefree_fraction_lower_bound (a : ℕ) (t : ℕ) (ht : t < 25)
    (hcross : t ≠ 7 ∧ t ≠ 18) (N : ℕ) (hN : N ≥ 100) :
    let B

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
Targeted query for Aristotle: Prove the cross-product constraint.

If a ≡ 7 (mod 25) and b ≢ 7, 18 (mod 25), then ab+1 might be squarefree.
This constrains the structure of extremal sets.
-/

import Mathlib.Data.Nat.Prime.Basic
import Mathlib.Data.Nat.Squarefree
import Mathlib.Data.Finset.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.ZMod.Basic


namespace Erdos.Problem848.SieveQuery2

/-- Non-squarefree product property: ab+1 is not squarefree for all a,b in A. -/
def NonSquarefreeProductProp (A : Finset ℕ) : Prop :=
  ∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)

/-- Key structural lemma: If a ≡ 7 (mod 25) and b ≡ t (mod 25) where t ∉ {7, 18},
    then ab + 1 ≢ 0 (mod 25). -/
lemma cross_residue_not_div_25 (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) : ¬ (25 ∣ a * b + 1) := by
  intro hdiv
  have h0 : ((a * b + 1 : ℕ) : ZMod 25) = 0 :=
    (ZMod.natCast_eq_zero_iff (a * b + 1) 25).2 hdiv
  have haZ : (a : ZMod 25) = 7 := by
    have : a % 25 = 7 % 25 := by
      simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using ha
    exact (ZMod.natCast_eq_natCast_iff' a 7 25).2 this
  have h1 : (7 : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
    have : (a : ZMod 25) * (b : ZMod 25) + 1 = 0 := by
      simpa [Nat.cast_add, Nat.cast_mul, Nat.cast_one] using h0
    simpa [haZ] using this
  have h2 : (7 : ZMod 25) * (b : ZMod 25) = (-1 : ZMod 25) := by
    simpa using (eq_neg_of_add_eq_zero_left h1)
  have h187 : (18 : ZMod 25) * (7 : ZMod 25) = 1 := by native_decide
  have hbZ : (b : ZMod 25) = (7 : ZMod 25) := by
    -- Multiply `7*b=-1` by the inverse of `7` in `ZMod 25` (which is `18`).
    have hmul : (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) =
        (18 : ZMod 25) * (-1 : ZMod 25) := by
      simpa [mul_assoc] using congrArg (fun x => (18 : ZMod 25) * x) h2
    have hb' : (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
      have hmul' : ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
          (18 : ZMod 25) * (-1 : ZMod 25) := by
        calc
          ((18 : ZMod 25) * (7 : ZMod 25)) * (b : ZMod 25) =
              (18 : ZMod 25) * ((7 : ZMod 25) * (b : ZMod 25)) := mul_assoc _ _ _
          _ = (18 : ZMod 25) * (-1 : ZMod 25) := hmul
      have : (1 : ZMod 25) * (b : ZMod 25) = (18 : ZMod 25) * (-1 : ZMod 25) := by
        simpa [h187] using hmul'
      simpa using this
    -- `18 * (-1) = -18 = 7` in `ZMod 25`.
    exact hb'.trans (by native_decide : (18 : ZMod 25) * (-1 : ZMod 25) = (7 : ZMod 25))
  have hbmod : b % 25 = 7 := by
    have hb' : b % 25 = 7 % 25 := (ZMod.natCast_eq_natCast_iff' b 7 25).1 hbZ
    simpa [Nat.mod_eq_of_lt (by decide : 7 < 25)] using hb'
  exact hb.1 hbmod

/-- If b ≡ t (mod 25) with t ∉ {7, 18}, then for ab+1 to not be squarefree,
    it must be divisible by p² for some prime p ≠ 5. -/
lemma must_have_other_prime_square (a b : ℕ) (ha : a % 25 = 7)
    (hb : b % 25 ≠ 7 ∧ b % 25 ≠ 18) (hnsq : ¬ Squarefree (a * b + 1)) :
    ∃ p : ℕ, Nat.Prime p ∧ p ≠ 5 ∧ p^2 ∣ a * b + 1 := by
  classical
  have hnot : ¬ ∀ p : ℕ, Nat.Prime p → ¬p * p ∣ a * b + 1 := by
    intro hall
    exact hnsq ((Nat.squarefree_iff_prime_squarefree).2 hall)
  -- From `¬ Squarefree`, extract a prime square divisor.
  push_neg at hnot
  rcases hnot with ⟨p, hp, hpp⟩
  have h25 : ¬ (25 ∣ a * b + 1) := cross_residue_not_div_25 a b ha hb
  have hp2 : p ^ 2 ∣ a * b + 1 := by
    simpa [pow_two] using hpp
  refine ⟨p, hp, ?_, hp2⟩
  intro hp5
  subst hp5
  have : 25 ∣ a * b + 1 := by
    simpa [pow_two] using hp2
  exact (h25 this).elim

/- Aristotle found this block to be false. Here is a proof of the negation:

noncomputable section AristotleLemmas

/-
The number of $n < N$ such that $n \equiv r \pmod M$ is at most $N/M + 1$.
-/
lemma card_filter_mod_eq_le (N M r : ℕ) (hM : M > 0) :
    ((Finset.range N).filter (fun n => n % M = r)).card ≤ N / M + 1 := by
      -- The set of indices $n < N$ such that $n \equiv r \pmod{M}$ is a subset of the set $\{kM + r \mid k \in \mathbb{N}, kM + r < N\}$.
      have h_subset : Finset.filter (fun n => n % M = r) (Finset.range N) ⊆ Finset.image (fun k => k * M + r) (Finset.range (N / M + 1)) := by
        exact fun x hx => Finset.mem_image.mpr ⟨ x / M, Finset.mem_range.mpr ( Nat.lt_succ_of_le ( Nat.div_le_div_right <| Finset.mem_range_le <| Finset.mem_filter.mp hx |>.1 ) ), by linarith [ Nat.mod_add_div x M, Finset.mem_filter.mp hx |>.2 ] ⟩;
      exact le_trans ( Finset.card_le_card h_subset ) ( Finset.card_image_le.trans ( by norm_num ) )

/-
For coprime $n, m$, there is exactly one $x < nm$ such that $x \equiv a \pmod n$ and $x \equiv b \pmod m$.
-/
lemma card_filter_crt (n m a b : ℕ) (hn : n > 0) (hm : m > 0) (h_cop : Nat.Coprime n m) :
    ((Finset.range (n * m)).filter (fun x => x % n = a % n ∧ x % m = b % m)).card = 1 := by
      -- By the Chinese Remainder Theorem, there exists a unique solution modulo $nm$ for the system of congruences $x \equiv a \pmod{n}$ and $x \equiv b \pmod{m}$.
      obtain ⟨x₀, hx₀⟩ : ∃ x₀ < n * m, x₀ % n = a % n ∧ x₀ % m = b % m := by
        have := Nat.chineseRemainder h_cop a b;
        exact ⟨ this.val % ( n * m ), Nat.mod_lt _ ( Nat.mul_pos hn hm ), by simpa [ Nat.ModEq, Nat.mod_mod ] using this.2.1, by simpa [ Nat.ModEq, Nat.mod_mod ] using this.2.2 ⟩;
      -- Since $x \equiv x₀ \pmod{n}$ and $x \equiv x₀ \pmod{m}$, and $n$ and $m$ are coprime, it follows that $x \equiv x₀ \pmod{nm}$.
      have h_cong : ∀ x, x % n = a % n → x % m = b % m → x % (n * m) = x₀ % (n * m) := by
        intros x hx_n hx_m;
        rw [ Nat.ModEq.symm ];
        rw [ ← Nat.modEq_and_modEq_iff_modEq_mul ];
        · exact ⟨ hx₀.2.1.trans hx_n.symm, hx₀.2.2.trans hx_m.symm ⟩;
        · assumption;
      rw [ Finset.card_eq_one ];
      exact ⟨ x₀, Finset.eq_singleton_iff_unique_mem.mpr ⟨ Finset.mem_filter.mpr ⟨ Finset.mem_range.mpr hx₀.1, hx₀.2.1, hx₀.2.2 ⟩, fun x hx => by have := h_cong x ( Finset.mem_filter.mp hx |>.2.1 ) ( Finset.mem_filter.mp hx |>.2.2 ) ; rw [ Nat.mod_eq_of_lt ( Finset.mem_range.mp ( Finset.mem_filter.mp hx |>.1 ) ), Nat.mod_eq_of_lt hx₀.1 ] at this; linarith ⟩ ⟩

/-
The number of $x < p^2$ such that $p^2 \mid ax+1$ is at most 1.
-/
lemma linear_cong_count (a p : ℕ) (hp : Nat.Prime p) :
    ((Finset.range (p^2)).filter (fun x => p^2 ∣ a * x + 1)).card ≤ 1 := by
      by_contra h_contra;
      -- If $p \nmid a$, then $\gcd(a, p^2) = 1$. The congruence $ax \equiv -1 \pmod{p^2}$ has a unique solution in `range (p^2)`.
      have h_unique : ∀ x y : ℕ, x < p ^ 2 → y < p ^ 2 → p ^ 2 ∣ a * x + 1 → p ^ 2 ∣ a * y + 1 → x = y := by
        intros x y hx hy hx' hy'
        have h_cong : a * x ≡ a * y [MOD p ^ 2] := by
          rw [ Nat.modEq_iff_dvd ];
          simpa using dvd_sub ( Int.natCast_dvd_natCast.mpr hy' ) ( Int.natCast_dvd_natCast.mpr hx' );
        -- Since $p$ is prime and does not divide $a$, we can divide both sides of the congruence $a * x ≡ a * y [MOD p^2]$ by $a$.
        have h_div : x ≡ y [MOD p ^ 2] := by
          rw [ Nat.modEq_iff_dvd ] at *;
          have h_div : Int.gcd (p ^ 2 : ℤ) (a : ℤ) = 1 := by
            exact_mod_cast Nat.Coprime.pow_left 2 <| hp.coprime_iff_not_dvd.mpr fun h => by have := Nat.dvd_trans ( dvd_pow_self p two_ne_zero ) hx'; simp_all +decide [ Nat.dvd_add_right, dvd_mul_of_dvd_left ] ;
          exact Int.dvd_of_dvd_mul_right_of_gcd_one ( by simpa [ mul_sub ] using h_cong ) h_div;
        exact Nat.mod_eq_of_lt hx ▸ Nat.mod_eq_of_lt hy ▸ h_div;
      exact h_contra ( Finset.card_le_one.mpr fun x hx y hy => h_unique x y ( Finset.mem_range.mp ( Finset.mem_filter.mp hx |>.1 ) ) ( Finset.mem_range.mp ( Finset.mem_filter.mp hy |>.1 ) ) ( Finset.mem_filter.mp hx |>.2 ) ( Finset.mem_filter.mp hy |>.2 ) )

/-
If we filter `range (n*m)` by a fixed residue mod `n` and a set of residues mod `m` of size at most 1, the result has size at most 1.
-/
lemma filter_crt_le_1 (n m : ℕ) (S : Finset ℕ) (a : ℕ) (hn : n > 0) (hm : m > 0) (h_cop : Nat.Coprime n m)
    (hS : S ⊆ Finset.range m) (hS_card : S.card ≤ 1) :
    ((Finset.range (n * m)).filter (fun x => x % n = a % n ∧ (x % m) ∈ S)).card ≤ 1 := by
      -- If $S = \emptyset$, then the filter condition $(x \% m \in S)$ is always false, so the set is empty, cardinality 0.
      by_cases hS_empty : S = ∅;
      · aesop;
      · -- Since $S$ is nonempty and has at most one element, there exists a unique $s \in S$.
        obtain ⟨s, hs⟩ : ∃ s, S = {s} := by
          exact Finset.card_eq_one.mp ( le_antisymm hS_card ( Finset.card_pos.mpr ( Finset.nonempty_of_ne_empty hS_empty ) ) );
        -- By `card_filter_crt`, this count is exactly 1.
        have h_crt : ((Finset.range (n * m)).filter (fun x => x % n = a % n ∧ x % m = s)).card = 1 := by
          convert card_filter_crt n m a s hn hm h_cop using 1;
          simp +decide [ Nat.mod_eq_of_lt ( Finset.mem_range.mp ( hS ( hs.symm ▸ Finset.mem_singleton_self _ ) ) ) ];
        aesop

/-
The number of $x < 25p^2$ such that $x \equiv t \pmod{25}$ and $p^2 \mid ax+1$ is at most 1.
-/
lemma bad_b_mod_25_p_sq_card (a t p : ℕ) (hp : Nat.Prime p) (hp5 : p ≠ 5) :
    ((Finset.range (25 * p^2)).filter (fun x => x % 25 = t ∧ p^2 ∣ a * x + 1)).card ≤ 1 := by
      have h_crt : Finset.card (Finset.filter (fun x => x % 25 = t % 25 ∧ p ^ 2 ∣ a * x + 1) (Finset.range (25 * p ^ 2))) ≤ 1 := by
        -- Let $S = \{s \in \text{range}(p^2) \mid p^2 \mid as+1\}$. By `linear_cong_count`, $|S| \le 1$.
        have hS : Finset.card (Finset.filter (fun s => p ^ 2 ∣ a * s + 1) (Finset.range (p ^ 2))) ≤ 1 := by
          convert linear_cong_count a p hp using 1;
        have h_crt : Finset.card (Finset.filter (fun x => x % 25 = t % 25 ∧ x % p ^ 2 ∈ Finset.filter (fun s => p ^ 2 ∣ a * s + 1) (Finset.range (p ^ 2))) (Finset.range (25 * p ^ 2))) ≤ 1 := by
          convert filter_crt_le_1 25 ( p ^ 2 ) ( Finset.filter ( fun s => p ^ 2 ∣ a * s + 1 ) ( Finset.range ( p ^ 2 ) ) ) t ( by decide ) ( pow_pos hp.pos 2 ) ( by simpa [ Nat.coprime_comm ] using Nat.Coprime.pow_left 2 <| show Nat.Coprime 5 p from Nat.Prime.coprime_iff_not_dvd ( by decide ) |>.2 fun h => hp5 <| by have := Nat.prime_dvd_prime_iff_eq ( by decide : Nat.Prime 5 ) hp; tauto ) ( Finset.filter_subset _ _ ) hS using 1;
        refine le_trans ?_ h_crt;
        refine Finset.card_mono ?_;
        simp +contextual [ Finset.subset_iff ];
        exact fun x hx₁ hx₂ hx₃ => ⟨ Nat.mod_lt _ ( pow_pos hp.pos _ ), by simpa [ Nat.dvd_iff_mod_eq_zero, Nat.add_mod, Nat.mul_mod, Nat.mod_eq_of_lt ( show x % p ^ 2 < p ^ 2 from Nat.mod_lt _ ( pow_pos hp.pos _ ) ) ] using hx₃ ⟩;
      exact le_trans ( Finset.card_le_card fun x hx => by aesop ) h_crt

/-
The number of $b < N$ such that $b \equiv t \pmod{25}$ and $p^2 \mid ab+1$ is at most $N/(25p^2) + 1$.
-/
lemma count_bad_b (a t N p : ℕ) (hp : Nat.Prime p) (hp5 : p ≠ 5) :
    ((Finset.range N).filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1)).card ≤ N / (25 * p^2) + 1 := by
      -- By `bad_b_mod_25_p_sq_card`, the number of such $b$ in any interval of length $25p^2$ is at most 1.
      have h_period : ∀ k : ℕ, ((Finset.Ico (k * (25 * p^2)) ((k + 1) * (25 * p^2))).filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1)).card ≤ 1 := by
        intro k
        have h_period : ((Finset.range (25 * p^2)).filter (fun x => x % 25 = t ∧ p^2 ∣ a * x + 1)).card ≤ 1 := by
          exact?;
        -- By periodicity, the number of solutions in each interval of length $25p^2$ is the same.
        have h_periodic : ((Finset.Ico (k * (25 * p^2)) ((k + 1) * (25 * p^2))).filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1)).card = ((Finset.range (25 * p^2)).filter (fun x => x % 25 = t ∧ p^2 ∣ a * (x + k * (25 * p^2)) + 1)).card := by
          rw [ Finset.card_filter, Finset.card_filter ];
          rw [ Finset.sum_Ico_eq_sum_range ] ; norm_num [ add_mul, add_comm, add_left_comm, add_assoc ];
          norm_num [ Nat.add_mod, Nat.mul_mod ];
        simp_all +decide [ mul_add, Nat.dvd_iff_mod_eq_zero, Nat.add_mod, Nat.mul_mod ];
      -- By partitioning the range [0, N) into intervals of length 25p², we can apply the periodicity result to each interval.
      have h_partition : ((Finset.range N).filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1)).card ≤ Finset.sum (Finset.range (N / (25 * p^2) + 1)) (fun k => ((Finset.Ico (k * (25 * p^2)) ((k + 1) * (25 * p^2))).filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1)).card) := by
        have h_partition : Finset.filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1) (Finset.range N) ⊆ Finset.biUnion (Finset.range (N / (25 * p^2) + 1)) (fun k => Finset.filter (fun b => b % 25 = t ∧ p^2 ∣ a * b + 1) (Finset.Ico (k * (25 * p^2)) ((k + 1) * (25 * p^2)))) := by
          intro b hb; simp_all +decide [ Finset.subset_iff ] ;
          exact ⟨ b / ( 25 * p ^ 2 ), Nat.lt_succ_of_le ( Nat.div_le_div_right hb.1.le ), Nat.div_mul_le_self _ _, by linarith [ Nat.div_add_mod b ( 25 * p ^ 2 ), Nat.mod_lt b ( show 25 * p ^ 2 > 0 by exact mul_pos ( by decide ) ( pow_pos hp.pos 2 ) ) ] ⟩;
        exact le_trans ( Finset.card_le_card h_partition ) ( Finset.card_biUnion_le );
      exact h_partition.trans ( le_trans ( Finset.sum_le_sum fun _ _ => h_period _ ) ( by norm_num ) )

/-
There are exactly 4 numbers less than 100 that are congruent to t mod 25.
-/
lemma card_filter_range_100_mod_25 (t : ℕ) (ht : t < 25) :
    ((Finset.range 100).filter (fun b => b % 25 = t)).card = 4 := by
      decide +revert

/-
There exists a natural number $a$ such that $4 \mid 25a+1$, $9 \mid 50a+1$, and $49 \mid 75a+1$.
-/
lemma exists_bad_a : ∃ a : ℕ, 4 ∣ a * 25 + 1 ∧ 9 ∣ a * 50 + 1 ∧ 49 ∣ a * 75 + 1 := by
  -- Let's choose any solution $a$ to the system of congruences.
  obtain ⟨a, ha⟩ : ∃ a, a ≡ 3 [MOD 4] ∧ a ≡ 7 [MOD 9] ∧ a ≡ 32 [MOD 49] := by
    by_contra htra;
    -- We need to find $a$ such that $a \equiv 3 \pmod{4}$, $a \equiv 7 \pmod{9}$, and $a \equiv 32 \pmod{49}$.
    have h_crt : ∃ a : ℕ, a ≡ 3 [MOD 4] ∧ a ≡ 7 [MOD 9] ∧ a ≡ 32 [MOD 49] := by
      have h4 : ∃ x, x ≡ 3 [MOD 4] ∧ x ≡ 7 [MOD 9] := by
        exists 7 + 9 * 1;
        norm_num [ Nat.ModEq ] at htra ⊢;
        exact htra ( Nat.findGreatest ( fun x => x % 4 = 3 ∧ x % 9 = 7 ∧ x % 49 = 32 ) 4999 ) ( by native_decide ) ( by native_decide ) ( by native_decide )
      obtain ⟨x, hx⟩ := h4
      have h9 : ∃ y, y ≡ x [MOD (4 * 9)] ∧ y ≡ 32 [MOD 49] := by
        have h9 : Nat.gcd (4 * 9) 49 = 1 := by
          grind;
        have := Nat.chineseRemainder h9;
        exact ⟨ _, this x 32 |>.2 ⟩
      obtain ⟨y, hy⟩ := h9
      exact ⟨y, by
        exact hy.1.of_dvd ( by decide ) |> Nat.ModEq.trans <| hx.1, by
        exact hy.1.of_dvd ( by decide ) |> Nat.ModEq.trans <| hx.2, by
        exact hy.2⟩;
    contradiction;
  exact ⟨ a, by rw [ Nat.dvd_iff_mod_eq_zero ] ; rw [ Nat.add_mod, Nat.mul_mod ] ; rw [ ← Nat.mod_add_div a 4, ha.1 ] ; norm_num, by rw [ Nat.dvd_iff_mod_eq_zero ] ; rw [ Nat.add_mod, Nat.mul_mod ] ; rw [ ← Nat.mod_add_div a 9, ha.2.1 ] ; norm_num, by rw [ Nat.dvd_iff_mod_eq_zero ] ; rw [ Nat.add_mod, Nat.mul_mod ] ; rw [ ← Nat.mod_add_div a 49, ha.2.2 ] ; norm_num ⟩

/-
There exists an $a$ such that for $N=100, t=0$, the fraction of squarefree $ab+1$ is less than $1/2$.
-/
lemma counterexample_lemma : ∃ (a : ℕ),
    let B := (Finset.range 100).filter (fun b => b % 25 = 0)
    let sqfree := B.filter (fun b => Squarefree (a * b + 1))
    (sqfree.card : ℚ) / B.card < 1/2 := by
      -- By `exists_bad_a`, there exists $a$ such that $4 \mid 25a+1$, $9 \mid 50a+1$, $49 \mid 75a+1$.
      obtain ⟨a, ha⟩ : ∃ a : ℕ, 4 ∣ a * 25 + 1 ∧ 9 ∣ a * 50 + 1 ∧ 49 ∣ a * 75 + 1 := by
        exact?;
      use a;
      -- For this $a$, we have $ab+1$ is not squarefree for $b \in \{25, 50, 75\}$.
      have h_not_sqfree : ∀ b ∈ ({25, 50, 75} : Finset ℕ), ¬Squarefree (a * b + 1) := by
        simp_all +decide [ Nat.squarefree_mul_iff ];
        exact ⟨ fun h => absurd ( h 2 ( by norm_num; omega ) ) ( by norm_num ), fun h => absurd ( h 3 ( by norm_num; omega ) ) ( by norm_num ), fun h => absurd ( h 7 ( by norm_num; omega ) ) ( by norm_num ) ⟩;
      -- Therefore, the only squarefree element in $B$ is $0$.
      have h_sqfree : ({b ∈ Finset.range 100 | b % 25 = 0} |>.filter (fun b => Squarefree (a * b + 1))) ⊆ {0} := by
        grind;
      exact lt_of_le_of_lt ( div_le_div_of_nonneg_right ( Nat.cast_le.mpr <| Finset.card_le_card h_sqfree ) <| Nat.cast_nonneg _ ) <| by rw [ div_lt_div_iff₀ ] <;> norm_cast;

/-
The statement `squarefree_fraction_lower_bound` is false.
-/
lemma squarefree_fraction_lower_bound_false : ¬ (∀ (a : ℕ) (t : ℕ) (ht : t < 25)
    (hcross : t ≠ 7 ∧ t ≠ 18) (N : ℕ) (hN : N ≥ 100),
    let B := (Finset.range N).filter (fun b => b % 25 = t)
    let sqfree := B.filter (fun b => Squarefree (a * b + 1))
    (sqfree.card : ℚ) / B.card ≥ 1/2) := by
      -- By lemma `counterexample_lemma`, there exists an $a$ such that for $N = 100$ and $t = 0$, the fraction is strictly less than $1/2$.
      obtain ⟨a, ha⟩ : ∃ a : ℕ, let B := (Finset.range 100).filter (fun b => b % 25 = 0); let sqfree := B.filter (fun b => Squarefree (a * b + 1)); (sqfree.card : ℚ) / B.card < 1 / 2 := by
        convert counterexample_lemma using 1;
      exact fun h => ha.not_le <| h a 0 ( by norm_num ) ( by norm_num ) 100 ( by norm_num )

end AristotleLemmas

/-
The fraction of b in a residue class (mod 25) for which ab+1 is squarefree
    is at least ∏_{p≠5}(1 - 1/p²) = 25/(4π²) ≈ 0.633.
-/
lemma squarefree_fraction_lower_bound (a : ℕ) (t : ℕ) (ht : t < 25)
    (hcross : t ≠ 7 ∧ t ≠ 18) (N : ℕ) (hN : N ≥ 100) :
    let B := (Finset.range N).filter (fun b => b % 25 = t)
    let sqfree := B.filter (fun b => Squarefree (a * b + 1))
    (sqfree.card : ℚ) / B.card ≥ 1/2 := by
  -- Wait, there's a mistake. We can actually prove the opposite.
  negate_state;
  -- Proof starts here:
  -- Let's choose any $a$ such that $4 \mid 25a+1$, $9 \mid 50a+1$, and $49 \mid 75a+1$.
  obtain ⟨a, ha⟩ : ∃ a : ℕ, 4 ∣ a * 25 + 1 ∧ 9 ∣ a * 50 + 1 ∧ 49 ∣ a * 75 + 1 := exists_bad_a;
  -- Let's choose $t = 0$.
  use a, 0;
  -- Let's choose $N = 100$.
  use by norm_num, by norm_num, 100;
  -- Let's calculate the set sqfree for this choice of a.
  have hsqfree : Finset.filter (fun b => Squarefree (a * b + 1)) {0, 25, 50, 75} ⊆ {0} := by
    simp_all +decide [ Finset.subset_iff ];
    exact ⟨ fun h => absurd ( h 2 ( by norm_num; omega ) ) ( by norm_num ), fun h => absurd ( h 3 ( by norm_num; omega ) ) ( by norm_num ), fun h => absurd ( h 7 ( by norm_num; omega ) ) ( by norm_num ) ⟩;
  simp_all +decide [ Finset.subset_iff ];
  field_simp;
  rw [ div_lt_iff₀ ] <;> norm_cast ; simp_all +decide [ Finset.filter ] ;
  erw [ Multiset.filter_singleton, Multiset.filter_singleton ] ; aesop_cat;

-/
/-- The fraction of b in a residue class (mod 25) for which ab+1 is squarefree
    is at least ∏_{p≠5}(1 - 1/p²) = 25/(4π²) ≈ 0.633. -/
lemma squarefree_fraction_lower_bound (a : ℕ) (t : ℕ) (ht : t < 25)
    (hcross : t ≠ 7 ∧ t ≠ 18) (N : ℕ) (hN : N ≥ 100) :
    let B := (Finset.range N).filter (fun b => b % 25 = t)
    let sqfree := B.filter (fun b => Squarefree (a * b + 1))
    (sqfree.card : ℚ) / B.card ≥ 1/2 := by
  sorry

end Erdos.Problem848.SieveQuery2
