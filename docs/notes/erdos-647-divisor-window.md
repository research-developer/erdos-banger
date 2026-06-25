# Erdős #647 — the divisor-window partial resolution

**Status:** #647 is **open**. This note records a *partial* result (a real theorem reducing the
problem) + machine evidence + the precise open core. It is the first research application of the
certify+Lean workbench (`certkit`, PR research-developer/erdos-banger#2). The full Mathlib proof
of the partial theorem is tracked in Linear **MATH-1**.

## Problem

Let `τ(n)` be the number of divisors of `n`. **Is there some `n > 24` with**
`max_{m<n} (m + τ(m)) ≤ n + 2`? Conjecturally **no** — 24 is the last such `n`.

## Reformulation

Let `slack(n) = max_{m<n} (τ(m) − (n − m))`. Since `max_{m<n}(m+τ(m)) = n + slack(n)`, the
property is exactly `slack(n) ≤ 2`. The negation we want for `n > 24` is `slack(n) ≥ 1`-and-more;
concretely **we want `∃ m < n` with `m + τ(m) ≥ n + 3`** (i.e. `slack(n) ≥ 3`).

## Exact-integer evidence (this session, zero-float divisor sieve)

To `N = 5×10⁷`:
- **No solution** with `n > 24` (`slack ≤ 2` never occurs).
- The **only** `n > 24` with `slack ≤ 3` are **`{35, 36, 48, 120}`** — all `≤ 120`.
- `slack(n) ≥ 5` for **every** `120 < n ≤ 5×10⁷` (the margin grows; max observed `slack = 671`).

Reproducible via `certkit/sieve647.py` (`verify_647_bound`), the independent exact oracle behind
the bounded Lean certificate.

## The partial theorem (what the divisor window proves)

> **Theorem.** For every `n > 24` with `n − 1` **not prime**, there is `m < n` with
> `m + τ(m) ≥ n + 3` (so `n` is not a #647 solution).

*Proof.*
- If `τ(n−1) ≥ 4`, take `m = n−1`: then `m + τ(m) = (n−1) + τ(n−1) ≥ (n−1) + 4 = n + 3`.
- Otherwise `τ(n−1) ≤ 3`. As `n−1 ≥ 24` (so `≠ 1`, ruling out `τ=1`) and `n−1` is not prime
  (ruling out `τ=2`), we have `τ(n−1) = 3`, hence `n−1 = p²` for a prime `p ≥ 5`. Take
  `m = n−2 = p²−1`. Now `p` is odd so `p² ≡ 1 (mod 8)`, and `p ∤ 3` so `p² ≡ 1 (mod 3)`; thus
  **`24 ∣ p²−1`**. Every divisor of 24 then divides `p²−1`, so `τ(p²−1) ≥ τ(24) = 8`, giving
  `m + τ(m) ≥ (n−2) + 8 = n + 6 ≥ n + 3`. ∎

Both steps are elementary and verified computationally: every prime `p ≥ 5` has `24 ∣ p²−1` and
`τ(p²−1) ≥ 8`. This is the content being formalized in Lean+Mathlib under MATH-1 (lemmas:
`τ(n−1)≥4 ⇒ done`; `24 ∣ p²−1`; `24 ∣ k ⇒ 8 ≤ τ(k)`; assembly).

## Machine-checked bounded certificate (the workbench's W2 path)

`certkit` emits, kernel-checks, and pins two core-Lean certificates of the bounded statement
`∀ n, 24 < n ≤ B → ∃ m < n, m + τ(m) ≥ n + 3`:
- `Cert/P647Bounded.lean` — pure `decide` (B = 50); `#print axioms` ⇒ **no axioms** (no
  `Lean.ofReduceBool`): pure-kernel.
- `Cert/P647BoundedNative.lean` — `native_decide` (B = 1000); axioms `[Lean.ofReduceBool,
  Lean.trustCompiler]` — the explicit trust delta.

So the bounded fact is machine-certified; the partial theorem above is the *unbounded* companion.

## The open core: safe primes (Sophie Germain)

Everything except `n − 1` prime is closed. For `n − 1 = p` prime, `m = n−2 = p−1` finishes
**unless** `τ(p−1) ≤ 4`, i.e. `p − 1 = 2q` with `q` prime — i.e. **`p` is a safe prime** (`q`
Sophie Germain). So **#647's open core sits exactly on the safe primes** — which is why it
resists an elementary closure (safe-prime distribution is itself open). This ties directly to the
RationAll twin-prime lattice line.

Even on the open core the conjecture holds empirically: the only tight prime case is `n = 48`
(`47 = 2·23 + 1`, a safe prime), rescued by `m = 45 = 3²·5` (`τ = 6`, distance 3 ⇒ `slack = 3`).
For safe primes giving `n > 120`, the rescuer always exists in range (`slack ≥ 5`).

## Pointers
- **MATH-1** (Linear) — full Lean+Mathlib proof of the partial theorem (in progress, background).
- `certkit/lean/Cert/P647Bounded*.lean` — the bounded kernel certificates.
- `certkit/sieve647.py` — the exact oracle (evidence above).
- decide-and-certify: **abstains** on the universal statement (out of fragment); for the universal
  `24 ∣ p²−1` it over-proposes `by omega` (which fails — `p²` is nonlinear), so the lemmas genuinely
  need Mathlib. Only concrete closed instances (`47² % 24 = 1`) are `by decide`-recognized.
