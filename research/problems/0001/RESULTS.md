# Erdős Problem #1 — Distinct Subset Sums: exact computational study

**Status: OPEN problem. This is exact data + verification of known results, NOT a solution.**

Erdős Problem #1 (he offered \$500). A finite set `A` of positive integers is
**sum-distinct** (has the *distinct subset sums*, DSS, property) if all `2^|A|`
subset sums are pairwise distinct. Erdős conjectured that every sum-distinct set
of size `n` has largest element `≫ 2^n`; equivalently

```
f(n) := min over sum-distinct sets A with |A| = n  of  max(A)
```

satisfies `f(n) ≥ c·2^n` for an absolute constant `c > 0`. This is **OEIS
[A276661](https://oeis.org/A276661)**. The conjecture is unresolved.

All arithmetic in the verifier and the search is **exact Python `int`** — subset
sums and comparisons are exact integers, no floating point. `float()` appears
only when printing the ratio `max(A)/2^n` for human reading.

Reproduce: `python3 erdos1_dss.py --nmax 9` (script in this directory).

---

## Deliverable 1 — exact DSS verifier

`is_sum_distinct(A)` uses a **bitmask frontier**: an `int` whose bit `i` is set
iff value `i` is an achievable subset sum of the elements seen so far. Adding
element `a` is `frontier |= frontier << a`; a subset-sum collision occurs iff
`frontier & (frontier << a) != 0`. Exact big-integer arithmetic, early-exit on
first collision.

Cross-checked against **two independent implementations** — an explicit
`set`-of-sums frontier, and a full `2^n` brute-force enumeration — on every unit
test. All three agree on all cases.

| set | `is_sum_distinct` | brute force | expected |
|---|---|---|---|
| `{1,2,4,8}` | True | True | True |
| `{1,2,3}` (1+2=3) | False | False | False |
| `{1}` | True | True | True |
| `{2,3,4}` | True | True | True |
| `{3,5,6,7}` | True | True | True |
| `{1,5,10,11}` (1+10=11) | False | False | False |
| `{2,3,5}` (2+3=5) | False | False | False |
| `{1,2,4,8,16}` | True | True | True |
| `{6,9,11,12,13}` (Conway–Guy n=5) | True | True | True |
| `{3,6,9}` (3+6=9) | False | False | False |

**All verifier unit tests PASS.** Additionally, every Conway–Guy set for
`n = 1…24` is confirmed sum-distinct by the verifier.

---

## Deliverable 3 — record constructions (descent below `2^{n-1}`)

`conway_guy(n)` reconstructs **OEIS [A005318](https://oeis.org/A005318)** via the
recurrence `u(0)=0, u(1)=1, u(k)=2u(k-1) − u(k-1-r)` with `r = round(√(2(k-1)))`,
and the set `S_n = { u(n) − u(n-i) : i=1..n }`. **For all `n = 1…24`,
`max(S_n)` matches A005318 exactly and `S_n` is verified sum-distinct.**

| n | powers-of-2 max | `/2^n` | Conway–Guy max | `/2^n` | DSS? |
|---:|---:|---:|---:|---:|:--:|
| 4 | 8 | 0.5000 | 7 | 0.4375 | ✓ |
| 5 | 16 | 0.5000 | 13 | 0.4062 | ✓ |
| 6 | 32 | 0.5000 | 24 | 0.3750 | ✓ |
| 7 | 64 | 0.5000 | 44 | 0.3438 | ✓ |
| 8 | 128 | 0.5000 | 84 | 0.3281 | ✓ |
| 9 | 256 | 0.5000 | 161 | 0.3145 | ✓ |
| 10 | 512 | 0.5000 | 309 | 0.3018 | ✓ |
| 12 | 4096 | 0.5000 | 1164 | 0.2842 | ✓ |
| 16 | 65536 | 0.5000 | 17305 | 0.2641 | ✓ |
| 20 | 1048576 | 0.5000 | 267420 | 0.2550 | ✓ |
| 24 | 16777216 | 0.5000 | 4172701 | 0.2487 | ✓ |

The **descent is explicit**: powers of two sit exactly at `0.5·2^n`; Conway–Guy
drops monotonically below, to `≈ 0.249·2^n` by `n=24` (limit `≈ 0.234`). Bohman
(1998) gives a construction reaching `≈ 0.22·2^n` asymptotically — confirming
Conway–Guy, though long conjectured optimal, is **not** asymptotically optimal.
(A Bohman-set reconstruction was not added here; the Conway–Guy descent already
demonstrates `max < 2^{n-1}` and is exactly verified.)

---

## Deliverable 2 — exhaustive `f(n)` (exact search) + Deliverable 4 cross-check

`f(n)` is computed **exactly** by branch-and-bound over strictly-increasing
size-`n` sets, using the bitmask frontier to prune any partial set that already
violates DSS, and the Conway–Guy max as a fixed upper bound. The search is
**parallelized** over leading-element prefixes (independent subtrees) across the
machine's cores. The returned witness for every `n` is independently
re-verified (bitmask + set-frame, plus brute force for `n ≤ 12`).

`A276661` (= `f(n)`) is **OEIS-confirmed only through `n = 10`** (the b-file
stops at 10). Values shown for `A276661` below are the OEIS-confirmed ones.
`CG = A005318` (Conway–Guy max) is shown alongside; Conway–Guy is proven optimal
(`= f(n)`) only for `n ≤ 8` (Lunnon 1988) and coincides numerically with the
known `f(n)` through `n = 11`.

<!-- RESULTS_TABLE_START -->
| n | f(n) (this search, exact) | f(n)/2^n | A276661 (OEIS) | Conway–Guy max | status |
|---:|---:|---:|---:|---:|:--|
| 1 | 1 | 0.50000 | 1 | 1 | OEIS-match |
| 2 | 2 | 0.50000 | 2 | 2 | OEIS-match |
| 3 | 4 | 0.50000 | 4 | 4 | OEIS-match |
| 4 | 7 | 0.43750 | 7 | 7 | OEIS-match |
| 5 | 13 | 0.40625 | 13 | 13 | OEIS-match |
| 6 | 24 | 0.37500 | 24 | 24 | OEIS-match |
| 7 | 44 | 0.34375 | 44 | 44 | OEIS-match |
| 8 | 84 | 0.32812 | 84 | 84 | OEIS-match |
<!-- RESULTS_TABLE_END -->

**Optimal witness sets found by the exhaustive search** (these *are* minimal-max
sum-distinct sets; each re-verified independently):

| n | f(n) | witness (one optimal set) |
|---:|---:|:--|
| 1 | 1 | `{1}` |
| 2 | 2 | `{1,2}` |
| 3 | 4 | `{2,3,4}` |
| 4 | 7 | `{3,5,6,7}` |
| 5 | 13 | `{6,9,11,12,13}` |
| 6 | 24 | `{11,17,20,22,23,24}` |
| 7 | 44 | `{20,31,37,40,42,43,44}` |
| 8 | 84 | `{40,60,71,77,80,82,83,84}` |

**Cross-check vs OEIS A276661: exact match for every `n` reached (1…8).**
No mismatches.

**`n = 9`** was attempted but **not completed within the ~20–30 min compute
box**: the search tree below the bound 161 is ≈ 2×10¹⁰ nodes (the node count
grows ≈ 200× per unit `n`), which exceeded the budget even parallelized across
~16 cores (it had consumed >100 core-minutes and was still running when
stopped). The exhaustive search therefore *establishes* `f(n)` here for
`1 ≤ n ≤ 8`. For reference, OEIS gives `f(9) = 161` and `f(10) = 309`
(both equal to the Conway–Guy max at those `n`); these are cited, not
re-derived by this run.

---

## Observations on the `f(n)/2^n` trend (relevant to the conjecture)

| n | f(n)/2^n |
|---:|---:|
| 1 | 0.50000 |
| 2 | 0.50000 |
| 3 | 0.50000 |
| 4 | 0.43750 |
| 5 | 0.40625 |
| 6 | 0.37500 |
| 7 | 0.34375 |
| 8 | 0.32812 |

Over the exactly-computed range the ratio `f(n)/2^n` **decreases monotonically**
but slowly, and stays well away from `0`. This is consistent with — and gives no
evidence against — Erdős's conjecture that `f(n)/2^n` is bounded below by a
positive constant. Extending the OEIS data (`f(9)=161 → 0.3145`,
`f(10)=309 → 0.3018`) continues the same slow decline toward the Conway–Guy
constant `≈ 0.234`. **Nothing here resolves the conjecture**; the open question
is precisely whether this ratio has a positive lower bound, and the data are far
too small-`n` to distinguish "bounded below" from "slowly → 0".

---

## Compute notes / honest limits

- **Method scaling.** The exact search is exponential. Node counts grow ≈ 200×
  per unit increase in `n` (n=6: ~7.9k nodes; n=7: ~5.1×10⁵; n=8: ~1.0×10⁸).
  Parallelizing over prefixes gives a near-linear speedup in core count
  (n=8: 46 s single-core → ~4 s on this machine).
- **Largest `n` reached exhaustively: `n = 8`** within the ~20–30 min box
  (`f(8) = 84`, witness `{40,60,71,77,80,82,83,84}`, ≈ 1.0×10⁸ search nodes,
  ~4 s on ~16 cores). `n = 9` was started but not finished (see above). The
  exhaustive search reproduces **OEIS A276661 with no deviation** for every `n`
  it completes (1…8).
- This study **verifies** known results (A276661 values, Conway–Guy/A005318
  constructions) with exact arithmetic and an independent code path; it makes
  **no claim** on the open conjecture.

### References
- OEIS A276661 — minimal largest element of a sum-distinct set of size n.
- OEIS A005318 — Conway–Guy sequence.
- F. Lunnon, *Integer sets with distinct subset sums*, Math. Comp. 50 (1988).
- T. Bohman, *A sum packing problem of Erdős and the Conway–Guy sequence* (1996/98).
