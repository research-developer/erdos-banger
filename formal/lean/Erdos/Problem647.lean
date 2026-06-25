/-
Problem 647: Erdős Problem #647 — a divisor window / "shifted divisor" statement.

Status: open (full problem); this file proves a PARTIAL theorem.
Linear: MATH-1.

# Informal statement (#647)
Let `τ(n)` denote the number of divisors of `n`. A natural "divisor window"
question asks, for `n`, whether there is some `m < n` with `n + 3 ≤ m + τ(m)`
— i.e. the value `m + τ(m)` reaches up into the window `[n+3, …)` from below.

# What this file proves (partial)
We treat the case where `n - 1` is *not* prime and `n` is reasonably large
(`n > 24`). The proof splits on `τ(n-1)`:

* **L1 (`window_high_divisor`)**: if `τ(n-1) ≥ 4`, take `m = n-1`; then
  `m + τ m = (n-1) + τ(n-1) ≥ (n-1) + 4 = n+3`.
* **L2 (`twentyfour_dvd_sq_sub_one`)**: every prime `p > 3` satisfies
  `24 ∣ p² - 1`. (Proved via the unit group of `ZMod 24`, whose every
  element squares to `1`, checked by `decide`.)
* **L3 (`eight_le_tau_of_24_dvd`)**: if `24 ∣ k` and `k ≠ 0` then `τ k ≥ 8`,
  since `(24).divisors ⊆ k.divisors` and `(24).divisors.card = 8`.
* **Main2 (`window_prime_square`)**: if `n - 1 = p²` for a prime `p > 3`,
  take `m = n - 2 = p² - 1`; then `24 ∣ m` (L2) so `τ m ≥ 8` (L3), giving
  `m + τ m ≥ (n-2) + 8 = n + 6 ≥ n + 3`.
* **L4 (`erdos647_window`)**: assembles L1 and Main2 for `n > 24` with
  `n-1` not prime, using the classification `τ k ≤ 3 ⇒ k` is prime or a prime
  square (`tau_le_three_imp_prime_or_prime_sq`).

EVERYTHING in this file is `sorry`-free: L1, L2, L3, Main2, the τ≤3
classification, and the assembled L4 all compile and pass `#print axioms`
with only `propext, Classical.choice, Quot.sound` (no `sorryAx`).

# Open core (not addressed here)
The remaining open core of #647 is the case where `n - 1` *is* prime, which
reduces to the structure of *safe primes* (`n - 1 = p` with `p = 2q + 1`,
`q` prime). That case is left open.
-/

import Mathlib.Algebra.Order.Ring.Star
import Mathlib.Analysis.Normed.Ring.Lemmas
import Mathlib.Data.Int.Star
import Mathlib.Data.ZMod.Basic
import Mathlib.NumberTheory.ArithmeticFunction.Misc
import Mathlib.Tactic.IntervalCases

namespace Erdos.Problem647

open Nat

/-- `τ n` is the number of divisors of `n` (Mathlib's `Nat.divisors`). -/
def tau (n : ℕ) : ℕ := n.divisors.card

/-! ## L1 — the easy high-divisor window -/

/-- **L1.** If `n - 1` has at least 4 divisors, then `m = n - 1` witnesses the
window: `m + τ m ≥ n + 3`. We assume `1 ≤ n` so that `n - 1 < n`. -/
theorem window_high_divisor (n : ℕ) (hn : 1 ≤ n) (h : 4 ≤ tau (n - 1)) :
    ∃ m, m < n ∧ n + 3 ≤ m + tau m := by
  refine ⟨n - 1, ?_, ?_⟩
  · omega
  · -- (n-1) + τ(n-1) ≥ (n-1) + 4 = n + 3
    have : n - 1 + 4 ≤ n - 1 + tau (n - 1) := by omega
    omega

/-! ## L2 — `24 ∣ p² - 1` for primes `p > 3` -/

/-- Every unit of `ZMod 24` squares to `1` (the group has exponent 2). Checked
by `decide` over the 8 units. -/
theorem units_zmod24_sq_eq_one : ∀ u : (ZMod 24)ˣ, u ^ 2 = 1 := by decide

/-- **L2.** For a prime `p > 3`, `24 ∣ p² - 1`. -/
theorem twentyfour_dvd_sq_sub_one {p : ℕ} (hp : p.Prime) (h3 : 3 < p) :
    24 ∣ p ^ 2 - 1 := by
  -- `p` is coprime to 24 (coprime to 2 and to 3), hence a unit in `ZMod 24`.
  have hcop : Nat.Coprime p 24 := by
    have h2 : Nat.Coprime p 2 := (Nat.coprime_primes hp Nat.prime_two).mpr (by omega)
    have h3' : Nat.Coprime p 3 := (Nat.coprime_primes hp Nat.prime_three).mpr (by omega)
    have hc : Nat.Coprime p (2 ^ 3 * 3) := Nat.Coprime.mul_right (h2.pow_right 3) h3'
    simpa using hc
  -- Build the unit and square it: every unit of `ZMod 24` squares to 1.
  have hunit : IsUnit (p : ZMod 24) := by
    rw [ZMod.isUnit_iff_coprime]; exact hcop
  obtain ⟨u, hu⟩ := hunit
  have hsq : (p : ZMod 24) ^ 2 = 1 := by
    rw [← hu, ← Units.val_pow_eq_pow_val, units_zmod24_sq_eq_one u, Units.val_one]
  -- Transfer back: (p^2 : ZMod 24) = 1, so 24 ∣ p^2 - 1.
  -- First (1 : ℕ) ≤ p^2 so ℕ-subtraction is genuine.
  have hple : 1 ≤ p ^ 2 := Nat.one_le_pow _ _ (by omega)
  have hcast : ((p ^ 2 : ℕ) : ZMod 24) = ((1 : ℕ) : ZMod 24) := by
    push_cast
    simpa using hsq
  -- Use modular-equality / cast-eq to get the divisibility of the difference.
  have hmod : (p ^ 2 : ℕ) ≡ 1 [MOD 24] := by
    have := (ZMod.natCast_eq_natCast_iff (p ^ 2) 1 24).1 hcast
    exact this
  -- 24 ∣ p^2 - 1 from the modular equality (p^2 ≥ 1).
  have : (1 : ℕ) ≡ p ^ 2 [MOD 24] := hmod.symm
  exact (Nat.modEq_iff_dvd' hple).1 this

/-! ## L3 — `24 ∣ k` forces at least 8 divisors -/

/-- `(24 : ℕ).divisors.card = 8`. -/
theorem divisors_card_24 : (Nat.divisors 24).card = 8 := by decide

/-- **L3.** If `24 ∣ k` (and `k ≠ 0`) then `τ k ≥ 8`, since the 8 divisors of
24 are all divisors of `k`. -/
theorem eight_le_tau_of_24_dvd {k : ℕ} (hk : k ≠ 0) (h : 24 ∣ k) : 8 ≤ tau k := by
  have hsub : (Nat.divisors 24) ⊆ k.divisors := Nat.divisors_subset_of_dvd hk h
  have hcard : (Nat.divisors 24).card ≤ k.divisors.card := Finset.card_le_card hsub
  rw [divisors_card_24] at hcard
  exact hcard

/-! ## Main2 — assemble L2 + L3 for prime squares -/

/-- **Main2.** If `n - 1 = p²` for a prime `p > 3`, then `m = n - 2 = p² - 1`
witnesses the window: `m + τ m ≥ n + 6 ≥ n + 3`. -/
theorem window_prime_square {n p : ℕ} (hp : p.Prime) (h3 : 3 < p)
    (hn : n - 1 = p ^ 2) : ∃ m, m < n ∧ n + 3 ≤ m + tau m := by
  -- From n - 1 = p^2 and p ≥ 4 we get n = p^2 + 1 ≥ 17.
  have hp4 : 4 ≤ p := by omega
  have hpsq : 16 ≤ p ^ 2 := by nlinarith
  have hnval : n = p ^ 2 + 1 := by omega
  -- The witness m = p^2 - 1 = n - 2.
  refine ⟨p ^ 2 - 1, ?_, ?_⟩
  · -- p^2 - 1 < p^2 + 1 = n
    omega
  · -- 24 ∣ p^2 - 1, so τ(p^2 - 1) ≥ 8.
    have hdvd : 24 ∣ p ^ 2 - 1 := twentyfour_dvd_sq_sub_one hp h3
    have hne : p ^ 2 - 1 ≠ 0 := by omega
    have h8 : 8 ≤ tau (p ^ 2 - 1) := eight_le_tau_of_24_dvd hne hdvd
    -- m + τ m ≥ (p^2 - 1) + 8 ≥ (n - 2) + 8 = n + 6 ≥ n + 3.
    omega

/-! ## L4 — assemble the partial theorem

The only non-elementary input is the classification of numbers with `τ ≤ 3`.
We isolate it as `tau_le_three_imp_prime_or_prime_sq`. -/

/-- **Classification.** A number `k ≥ 2` with `τ k ≤ 3` is either prime or the
square of a prime.

This is the standard divisor-count classification (`τ k = 2 ↔ k` prime and
`τ k = 3 ↔ k = p²`). Proof: via `Nat.card_divisors` the count equals
`∏_{p ∣ k} (vₚ(k) + 1)`; each factor is `≥ 2`, and `Finset.pow_card_le_prod`
gives `2^{#primeFactors} ≤ 3`, forcing a single prime factor, i.e.
`IsPrimePow k`. Writing `k = pᵉ`, `τ k = e + 1 ≤ 3` leaves `e ∈ {1, 2}`,
i.e. `k` prime or `k = p²`. -/
theorem tau_le_three_imp_prime_or_prime_sq {k : ℕ} (hk : 2 ≤ k)
    (h : tau k ≤ 3) : k.Prime ∨ ∃ p, p.Prime ∧ k = p ^ 2 := by
  have hk0 : k ≠ 0 := by omega
  set s := k.primeFactors with hs
  -- Each prime factor contributes a factor `≥ 2` to the divisor-count product.
  have hf : ∀ x ∈ s, 2 ≤ k.factorization x + 1 := by
    intro x hx
    rw [hs] at hx
    have hxp : x.Prime := Nat.prime_of_mem_primeFactors hx
    have hxd : x ∣ k := (Nat.mem_primeFactors.1 hx).2.1
    have : 0 < k.factorization x := hxp.factorization_pos_of_dvd hk0 hxd
    omega
  -- `2 ^ |s| ≤ ∏ (vₚ + 1) = τ k ≤ 3`, forcing `|s| ≤ 1`.
  have hpow : 2 ^ s.card ≤ ∏ x ∈ s, (k.factorization x + 1) :=
    Finset.pow_card_le_prod s _ 2 hf
  have hc : (∏ x ∈ s, (k.factorization x + 1)) ≤ 3 := by
    rw [hs, ← Nat.card_divisors hk0]; exact h
  have hcard_le : s.card ≤ 1 := by
    by_contra hcon
    push_neg at hcon
    have : (2 : ℕ) ^ 2 ≤ 2 ^ s.card := Nat.pow_le_pow_right (by norm_num) hcon
    omega
  -- `k ≥ 2` has a prime factor, so `|s| ≥ 1`; hence `|s| = 1`, i.e. `IsPrimePow k`.
  have hne : s.Nonempty := by rw [hs]; exact Nat.nonempty_primeFactors.2 (by omega)
  have hcard1 : s.card = 1 := le_antisymm hcard_le (Finset.card_pos.2 hne)
  have hpp : IsPrimePow k :=
    isPrimePow_iff_card_primeFactors_eq_one.2 (by rw [← hs]; exact hcard1)
  -- Unpack the prime power `k = p ^ e` with `p` prime and `e ≥ 1`.
  obtain ⟨p, e, hp, he, hpe⟩ := hpp
  have hpn : p.Prime := Nat.prime_iff.2 hp
  -- Compute `τ k = e + 1` from the divisors of a prime power, then bound `e`.
  have hdiv : tau k = e + 1 := by
    rw [tau, ← hpe, Nat.divisors_prime_pow hpn, Finset.card_map, Finset.card_range]
  rw [hdiv] at h
  -- `e + 1 ≤ 3` and `e ≥ 1` give `e = 1` (prime) or `e = 2` (prime square).
  have he2 : e ≤ 2 := by omega
  interval_cases e
  · left; rw [← hpe]; simpa using hpn
  · right; exact ⟨p, hpn, hpe.symm⟩

/-- **L4 (partial #647).** For `n > 24` with `n - 1` not prime, there is some
`m < n` with `n + 3 ≤ m + τ m`.

Proof: split on `τ (n-1)`. If `τ (n-1) ≥ 4`, use L1. Otherwise `τ (n-1) ≤ 3`;
since `n - 1 ≥ 24 ≥ 2` and is not prime, the classification gives
`n - 1 = p²` for a prime `p`, and `p² = n - 1 ≥ 24` forces `p ≥ 5 > 3`, so
Main2 applies. -/
theorem erdos647_window (n : ℕ) (hn : 24 < n) (hnp : ¬ (n - 1).Prime) :
    ∃ m, m < n ∧ n + 3 ≤ m + tau m := by
  by_cases hge : 4 ≤ tau (n - 1)
  · exact window_high_divisor n (by omega) hge
  · -- τ(n-1) ≤ 3 and n-1 ≥ 24 ≥ 2, not prime ⇒ n-1 = p^2 for prime p.
    have hle : tau (n - 1) ≤ 3 := by omega
    have hk2 : 2 ≤ n - 1 := by omega
    rcases tau_le_three_imp_prime_or_prime_sq hk2 hle with hpr | ⟨p, hp, hsq⟩
    · exact absurd hpr hnp
    · -- p^2 = n - 1 ≥ 24, so p ≥ 5 > 3.
      have h24 : 24 ≤ p ^ 2 := by omega
      have h3 : 3 < p := by nlinarith
      exact window_prime_square hp h3 hsq

end Erdos.Problem647
