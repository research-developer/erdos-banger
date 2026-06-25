# Problem 0001 — Distinct subset sums (Erdős #1, \$500, OPEN)

Exact-integer computational study. **Not a solution** — produces verifiable data.

- `erdos1_dss.py` — exact DSS verifier, exact `f(n)` branch-and-bound search
  (parallelized), Conway–Guy/A005318 reconstruction, and OEIS A276661
  cross-check. Run: `python3 erdos1_dss.py --nmax 9`.
- `RESULTS.md` — curated results: verifier tests, `f(n)` table with optimal
  witness sets, Conway–Guy descent ratios, A276661 cross-check, `f(n)/2^n`
  trend, and honest compute limits.

Statement: a set `A` of positive integers is *sum-distinct* if all `2^|A|`
subset sums are distinct; `f(n) = min over sum-distinct |A|=n of max(A)`. Erdős
conjectured `f(n) ≫ 2^n` (OEIS A276661). All search/verification arithmetic is
exact `int` (zero-float discipline).
