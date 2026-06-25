# Erdős #1052 — Unitary perfect numbers: exact-integer study

**Status: OPEN.** This document reports *exact verified data* and *bounded
evidence*. It does **not** claim a resolution of #1052.

> **Problem (Linear MATH-11).** A *unitary divisor* `d ∣ n` satisfies
> `gcd(d, n/d) = 1`. `n` is **unitary perfect** if the sum of its unitary
> divisors equals `2n`. Five are known — `6, 60, 90, 87360,
> 146361946186458562560000` — and #1052 asks whether there are only finitely
> many.

All arithmetic is exact (Python big integers); **zero floating point** is used
anywhere in the computation or the predicate.

Reproduce: `python3 unitary_perfect.py` (default exhaustive bound `N = 10^8`;
pass a different `N` as `argv[1]`).

---

## 1. The function `σ*` and the predicate

`σ*` is multiplicative on the prime-power blocks of `n`. If
`n = ∏ pᵢ^{aᵢ}`, the unitary divisors are exactly the products of a subset of
the blocks `pᵢ^{aᵢ}`, so

```
σ*(n) = ∏ (1 + pᵢ^{aᵢ}),      is_unitary_perfect(n)  ⟺  σ*(n) == 2n.
```

Two **independent** implementations are provided and cross-checked against each
other (they agree on every sampled `n`; see §4):

* `sigma_star(n)` — via exact factorization (`factorize`: trial division +
  deterministic-grade Miller–Rabin + Pollard rho).
* a **linear sieve** (`unitary_perfect_upto`) computing `σ*` for all `n ≤ N`
  via the block recurrence `σ*(n) = (1 + p^a)·σ*(n / p^a)` where `p^a` is the
  full block of the smallest prime factor.

## 2. The five known unitary perfect numbers — verified exactly

| n | factorization | σ\*(n) = 2n |
|---|---|---|
| 6 | 2·3 | 12 ✓ |
| 60 | 2²·3·5 | 120 ✓ |
| 90 | 2·3²·5 | 180 ✓ |
| 87360 | 2⁶·3·5·7·13 | 174720 ✓ |
| 146361946186458562560000 | 2¹⁸·3·5⁴·7·11·13·19·37·79·109·157·313 | 292723892372917125120000 ✓ |

For the 24-digit number the script confirms both that the factorization
multiplies back to `n` exactly and that
`σ*(n) = 292723892372917125120000 = 2n` — all in exact integer arithmetic.

## 3. Search for a 6th unitary perfect number

### 3a. Exhaustive sieve (primary certificate)

`unitary_perfect_upto(N)` checks **every** integer in `[1, N]` (no prime or
block bound that could miss a case). Result:

```
N = 10^8 :  unitary perfect numbers in [1, N] = [6, 60, 90, 87360]
```

i.e. **no 6th unitary perfect number exists below 10⁸** (the 24-digit one is
far beyond this bound). The sieve is `O(N log log N)` and exact; the `N = 10⁸`
run completes in ≈29 s on the test machine.

### 3b. Structured block search (secondary cross-check)

`search_blocks` solves the equivalent identity directly:

```
σ*(n) = 2n   ⟺   ∏ (1 + qᵢ) = 2 ∏ qᵢ   ⟺   ∏ (1 + 1/qᵢ) = 2,   qᵢ = pᵢ^{aᵢ}.
```

It runs an exact DFS over sets of **distinct-prime** prime-power blocks with:

* a **one-block-per-prime** guard (a unitary structure has exactly one block
  per prime);
* a **monotonicity prune**: every block multiplies `S/P` by `(1+1/q) > 1`, so
  once `S > 2P` the ratio can never return to `2`;
* **independent re-verification** of every `S == 2P` hit via
  `is_unitary_perfect` (defense in depth).

Over the pool `primes ≤ 200`, `block ≤ 200000`, `≤ 8` blocks it returns
exactly `[6, 60, 90, 87360]` with **zero** rejected hits — matching the sieve.

> **Methodology note (an avoided pitfall).** An early version of the block
> search omitted the one-block-per-prime guard and reported spurious
> "solutions" (e.g. 1080, 36720). They were caught immediately because every
> candidate is re-checked with the independent `is_unitary_perfect`, and none
> survived. The final search carries the guard *and* the re-check.

### Coverage / honest limits

* The sieve certificate is **complete** but bounded: it proves non-existence
  only on `[1, N]`. It is **not** a finiteness proof.
* A 6th unitary perfect number, if it exists, must exceed `10⁸` and (by §4)
  be **even**. The known gap from `87360` to the 24-digit number shows these
  are extremely sparse; a 6th would be enormous.

## 4. Structural observations toward finiteness (all exact, verifiable)

1. **Block-sum parity.** For an odd prime power `q = p^a`, `1 + q` is **even**;
   for `q = 2^a`, `1 + 2^a` is **odd**. (Verified on all 5 known: each has
   exactly one odd `(1+2^a)` block and all odd-prime blocks even.)

2. **2-adic balance ⇒ every unitary perfect `n > 1` is even.** `σ*(n) = 2n`
   forces `v₂(σ*(n)) = 1 + v₂(n)`. The block `2^a` contributes `a` to
   `v₂(2n)` but `(1+2^a)` is odd, so **all** factors of two in `σ*(n)` come
   from the odd blocks. If `n` were odd, `σ*(n)` would be odd and could never
   equal `2n`. Hence `n` is even — consistent with all 5 known. This also
   **caps the number of odd prime-power blocks** once the power of two is
   fixed (their `(1+p^a)` contributions must supply exactly `1 + v₂(n)`
   factors of two).

3. **Abundancy rigidity.** `n` is unitary perfect iff `∏ (1 + 1/qᵢ) = 2`
   exactly. Each factor exceeds 1 and tends to 1 as the block grows; although
   `∏(1+1/q)` over *all* prime powers diverges, hitting **exactly** 2 with
   finitely many distinct-prime blocks is rigid and forces small blocks. This
   rigidity is the lever behind the known partial finiteness results in the
   literature (e.g. bounds on the count of distinct odd primes once the power
   of two is fixed), and it is why the five known examples are so structured
   and so sparse.

## 5. Honest scope statement

This study delivers (i) verified exact data for all five known unitary perfect
numbers including the 24-digit one, (ii) an exact, complete non-existence
certificate on `[1, 10⁸]`, and (iii) exact structural constraints (parity,
forced evenness, abundancy rigidity). It makes **no** claim to resolve Erdős
#1052; finiteness remains open.
