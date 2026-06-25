# MATH-1 — Erdős Problem #647 partial theorem (Lean 4 + Mathlib)

**Status: DONE** — the full partial theorem is proved **sorry-free**. The
classification step originally flagged as possibly-isolatable
(`tau_le_three_imp_prime_or_prime_sq`) was successfully discharged, so there is
**no `sorry` anywhere** in the file.

- Worktree: `/Users/psentro/git/erdos-banger-math1`
- Branch: `math-1-647-divisor-window`
- File: `formal/lean/Erdos/Problem647.lean` (wired into `formal/lean/Erdos.lean`)
- Toolchain: Lean `v4.27.0`, Mathlib `v4.27.0` (per `formal/lean/lakefile.lean` / `lean-toolchain`)

## Definition

```lean
def tau (n : ℕ) : ℕ := n.divisors.card
```

## Theorems (all sorry-free)

```lean
-- L1
theorem window_high_divisor (n : ℕ) (hn : 1 ≤ n) (h : 4 ≤ tau (n - 1)) :
    ∃ m, m < n ∧ n + 3 ≤ m + tau m

-- helper for L2 (decide over the 8 units of ZMod 24)
theorem units_zmod24_sq_eq_one : ∀ u : (ZMod 24)ˣ, u ^ 2 = 1

-- L2
theorem twentyfour_dvd_sq_sub_one {p : ℕ} (hp : p.Prime) (h3 : 3 < p) :
    24 ∣ p ^ 2 - 1

-- helper for L3 (decide)
theorem divisors_card_24 : (Nat.divisors 24).card = 8

-- L3
theorem eight_le_tau_of_24_dvd {k : ℕ} (hk : k ≠ 0) (h : 24 ∣ k) : 8 ≤ tau k

-- Main2
theorem window_prime_square {n p : ℕ} (hp : p.Prime) (h3 : 3 < p)
    (hn : n - 1 = p ^ 2) : ∃ m, m < n ∧ n + 3 ≤ m + tau m

-- classification (was the candidate isolation point — proved sorry-free)
theorem tau_le_three_imp_prime_or_prime_sq {k : ℕ} (hk : 2 ≤ k)
    (h : tau k ≤ 3) : k.Prime ∨ ∃ p, p.Prime ∧ k = p ^ 2

-- L4 (assembled partial #647)
theorem erdos647_window (n : ℕ) (hn : 24 < n) (hnp : ¬ (n - 1).Prime) :
    ∃ m, m < n ∧ n + 3 ≤ m + tau m
```

### Hypothesis adjustments vs. the brief (documented)
- **L1**: stated with `(hn : 1 ≤ n)` instead of `(hn : 1 ≤ n - 1)`. With `n ≥ 1`,
  ℕ-subtraction gives `n - 1 < n` and `(n-1) + 4 = n + 3`, which is all L1 needs.
  This is strictly weaker/cleaner; nothing downstream needs the `n - 1 ≥ 1` form.
- Everything else matches the brief verbatim. L4 uses `n > 24` so that
  `n - 1 ≥ 24 ≥ 2` (classification applies) and `p² = n - 1 ≥ 24 ⇒ p ≥ 5 > 3`.

## Proof sketch of the (now-closed) classification
`Nat.card_divisors` rewrites `τ k = ∏_{p ∈ k.primeFactors} (vₚ(k)+1)`. Each
factor is `≥ 2`, so `Finset.pow_card_le_prod` gives `2^{#primeFactors} ≤ τ k ≤ 3`,
forcing `#primeFactors ≤ 1`; nonemptiness (`k ≥ 2`) gives `= 1`, i.e.
`IsPrimePow k` (`isPrimePow_iff_card_primeFactors_eq_one`). Writing `k = pᵉ`,
`τ k = e + 1` (`Nat.divisors_prime_pow`), and `e + 1 ≤ 3` with `e ≥ 1` leaves
`e = 1` (k prime) or `e = 2` (k = p²).

## Evidence

### Cache / build commands that worked
```
cd /Users/psentro/git/erdos-banger-math1/formal/lean
lake exe cache get        # → "No files to download" + "Decompressing 7869 file(s)" + "Completed successfully!"
lake build Erdos.Problem647   # → "✔ Built Erdos.Problem647" — exit 0, no warnings
lake build Erdos              # → "Build completed successfully (7905 jobs)" — exit 0
```
(`timeout` is not available on macOS; ran `lake exe cache get` directly.)

The only `sorry` warnings in the full-library build come from the **pre-existing**
`Erdos/Problem074_novel_experimental.lean` (unrelated to MATH-1). `Erdos.Problem647`
builds with **no warnings**.

### Axiom check (`#print axioms` via lean-lsp `lean_verify`)
Every theorem below depends ONLY on `[propext, Classical.choice, Quot.sound]` —
**no `sorryAx`**:
- `Erdos.Problem647.erdos647_window`  (the full assembled theorem)
- `Erdos.Problem647.tau_le_three_imp_prime_or_prime_sq`
- `Erdos.Problem647.twentyfour_dvd_sq_sub_one`
- `Erdos.Problem647.eight_le_tau_of_24_dvd`
- `Erdos.Problem647.window_prime_square`

### Sorry-free summary
| Lemma | sorry-free? | evidence |
|---|---|---|
| L1 `window_high_divisor` | ✅ | builds clean; axioms ok (via `erdos647_window` dep) |
| L2 `twentyfour_dvd_sq_sub_one` | ✅ | `lean_verify` → no `sorryAx` |
| L3 `eight_le_tau_of_24_dvd` | ✅ | `lean_verify` → no `sorryAx` |
| Main2 `window_prime_square` | ✅ | `lean_verify` → no `sorryAx` |
| classification | ✅ | `lean_verify` → no `sorryAx` |
| L4 `erdos647_window` | ✅ | `lean_verify` → no `sorryAx` |

## Open core (not addressed)
The remaining open core of #647 is the case `n - 1` **prime**, which reduces to
the structure of *safe primes* (`n - 1 = p`, `p = 2q + 1`, `q` prime). Left open.
