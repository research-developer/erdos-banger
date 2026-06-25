# Erdős #470 — Weird numbers: exact-integer computational study

**Status: OPEN.** This document reports *exact, verified computational evidence*.
It does **not** claim to resolve either part of the problem.

## The problem

A positive integer `n` is **weird** if it is

- **abundant**: `σ(n) ≥ 2n` (equivalently the proper-divisor sum `s(n) = σ(n) − n ≥ n`), **and**
- **not pseudoperfect** (a.k.a. not semiperfect): no subset of the proper divisors of `n` sums to `n`.

Erdős #470 asks:

- **(a)** Are there any **odd** weird numbers?
- **(b)** Are there infinitely many **primitive** weird numbers (a weird number none of whose proper divisors is itself weird)?

Both questions are open. (For (a), no odd weird number is known; searches in the
literature have reached roughly `10²¹` with none found. For (b), it is known that
there are infinitely many weird numbers; infinitude of *primitive* weird numbers
is the open part, though Melfi (2015) showed it follows from standard conjectures
on prime gaps.)

## Method — zero-float / exact integer throughout

All arithmetic is exact integer; there are no floating-point operations anywhere
in the decision path.

- **`σ(n)` and divisor lists** come from integer factorization (`sympy.factorint`),
  via the exact product `σ(∏ pᵢ^aᵢ) = ∏ (pᵢ^(aᵢ+1) − 1)/(pᵢ − 1)` in ℤ. For the
  large odd scan, `σ` is instead produced by an exact **divisor-sum sieve**
  (add `d` to every multiple of `d`), which avoids per-number factorization.
- **Pseudoperfect = exact subset-sum.** The decision "does some subset of the
  proper divisors sum to `n`?" is made with a **bitset dynamic program** over
  arbitrary-precision Python integers: bit `i` of `reachable` is set iff some
  subset sums to `i`; absorbing a divisor `d` is the single operation
  `reachable |= reachable << d` (masked to `[0, target]`). This is exact (no
  float, no randomness) and far faster than enumerating `2^k` subsets.
- **Complement optimization (exact).** A subset sums to `target` iff its
  complement sums to `total − target`. The DP is therefore run toward
  `min(target, total − target)`. For barely-abundant numbers — the overwhelming
  case, especially among odd numbers — `total − target = σ(n) − 2n` is tiny, so
  the DP word-count collapses from `O(target/64)` to `O((σ(n)−2n)/64)`. This was
  cross-checked element-for-element against a brute-force subset-enumeration
  oracle on 403 cases (including abundant numbers) with **0 disagreements**.

`is_weird(n)`, `is_pseudoperfect(n)`, `σ(n)`, `proper_divisors(n)`,
`odd_weird_search(...)`, and `primitive_weird_numbers(...)` are all in
[`weird.py`](./weird.py). Run `python3 weird.py --help` for options.

### Unit tests (all pass)

- `is_weird(70) == True` (smallest weird number).
- `is_weird(12) == False` — `12` is abundant but pseudoperfect (`1+2+3+6 = 12`).
- The proper divisors of `70` are `{1, 2, 5, 7, 10, 14, 35}` (sum `74 > 70`, so
  abundant) and **no** subset sums to `70` — so `70` is weird.
- Perfect numbers (`6`, `28`) are pseudoperfect, hence not weird, under either the
  strict (`σ > 2n`) or non-strict (`σ ≥ 2n`) abundance convention — the **weird
  set is identical** either way. We follow the brief's stated `σ(n) ≥ 2n`.

## Result 1 — weird & primitive enumeration up to 10⁶

| quantity | computed | OEIS reference | match |
|---|---:|---:|:---:|
| weird numbers `≤ 10⁶` (A006037) | **1765** | 1765 | ✅ exact, both directions |
| primitive weird `≤ 10⁶` (A002975) | **24** | 24 | ✅ exact, both directions |

The cross-check is a **full set comparison** (every computed term equals the OEIS
b-file term and vice-versa within range), not a prefix spot-check. The b-files
([`data/b006037.txt`](./data/b006037.txt), 10 000 terms;
[`data/b002975.txt`](./data/b002975.txt), 1161 terms) are bundled for
reproducibility.

- First weird numbers: `70, 836, 4030, 5830, 7192, 7912, 9272, 10430, 10570,
  10792, 10990, 11410, …` — matches **A006037**.
- Full computed lists: [`data/weird_le_1e6.txt`](./data/weird_le_1e6.txt) (1765
  values), [`data/primitive_weird_le_1e6.txt`](./data/primitive_weird_le_1e6.txt)
  (24 values).
- The 24 primitive weird numbers `≤ 10⁶`:
  `70, 836, 4030, 5830, 7192, 7912, 9272, 10792, 17272, 45356, 73616, 83312,
  91388, 113072, 243892, 254012, 338572, 343876, 388076, 519712, 539744, 555616,
  682592, 786208` — matches **A002975**.

## Result 2 — odd-weird search

Exact scan of **all odd** `n` in `[3, 49 999 999]` (sieve-σ abundance gate, then
complement-optimized exact subset-sum on each odd abundant candidate):

- **Bound reached: `n = 49 999 999`** (i.e. all odd `n < 5 × 10⁷`).
- Odd **abundant** numbers tested (the only weird candidates): **103 059**.
- **Odd weird numbers found: NONE.**

This **confirms** (does not extend) the known state: no odd weird number exists
below `5 × 10⁷`. The literature has pushed this past `~10²¹`; this run is a
self-contained exact re-verification at a modest bound, not a record. A single
odd weird number would settle (a) in the affirmative; none was found.

*Compute note:* the bottleneck is the pure-Python σ-sieve (re-swept per block),
not the subset-sum — abundance is rare among odds (~0.2 %) and barely-abundant,
so the complement-optimized DP is cheap per candidate. The full odd scan took
~6.5 min single-threaded; a numpy/native sieve would extend the bound by orders
of magnitude.

## Result 3 — primitive-weird growth (evidence bearing on (b))

Cumulative count of **primitive** weird numbers below `10^k` (≤ 10⁶ computed and
verified here; larger decades read from the verified OEIS A002975 b-file):

| `k` | primitive weird `< 10^k` | ratio to previous decade |
|---:|---:|---:|
| 2 | 1 | — |
| 3 | 2 | 2.00 |
| 4 | 7 | 3.50 |
| 5 | 13 | 1.86 |
| 6 | **24** | 1.85 |
| 7 | 48 | 2.00 |
| 8 | 85 | 1.77 |
| 9 | 152 | 1.79 |
| 10 | 276 | 1.82 |
| 11 | 499 | 1.81 |
| 12 | 881 | 1.77 |
| 13 | 1161* | — (b-file ends mid-decade) |

The per-decade multiplier is strikingly stable at **≈ 1.8** across nine decades.
This steady, non-decaying growth is **empirical evidence consistent with there
being infinitely many primitive weird numbers** (part (b)) — but it is *only*
evidence, not a proof. (Counts `≤ 10⁶` are from this study's exact enumeration;
larger ones are from the OEIS b-file, which we verified term-for-term against our
own computation in its overlap.)

## Honest limits

- The odd-weird negative result holds only for odd `n < 5 × 10⁷`. It does **not**
  bear on the existence of odd weird numbers above that bound; (a) remains open.
- The growth observation in Result 3 is heuristic. It does not constitute a proof
  of (b). It is consistent with — but independent of — Melfi's conditional result.
- No claim is made that #470 is resolved in any part. These are exact data and
  cross-checks intended as a reproducible evidence base.

## Reproduce

```bash
# enumeration + full b-file cross-check + dumps (≈25 s)
python3 weird.py --weird-limit 1000000 \
    --bfile-weird data/b006037.txt --bfile-prim data/b002975.txt \
    --dump-weird /tmp/w.txt --dump-prim /tmp/p.txt --skip-odd

# odd-weird scan to 5e7 (≈6.5 min single-threaded)
python3 weird.py --skip-weird --odd-limit 50000000 --odd-report-every 1
```

Full captured run output: [`data/run_log.txt`](./data/run_log.txt).
