#!/usr/bin/env python3
"""
Erdos Problem #1 -- Distinct Subset Sums (sum-distinct sets).
Exact-integer computational study toward an OPEN problem.  NOT a solution.

------------------------------------------------------------------------------
THE PROBLEM
------------------------------------------------------------------------------
A finite set A of positive integers has the DISTINCT SUBSET SUMS (DSS,
"sum-distinct") property if all 2^|A| subset sums are pairwise distinct.
Erdos (offering $500) conjectured that any sum-distinct set of size n has a
largest element  >= c * 2^n  for an absolute constant c > 0.  Equivalently,

    f(n) := min over sum-distinct sets A with |A| = n  of  max(A)

satisfies  f(n) >> 2^n.  This is OEIS A276661.  The problem is OPEN; this
program produces exact data and verifies known constructions -- it does not
resolve the conjecture.

Baselines:
  * powers of two {1,2,...,2^(n-1)}  are sum-distinct with max = 2^(n-1).
  * Conway-Guy (OEIS A005318) sets are sum-distinct with smaller max,
    ~0.234 * 2^n; Bohman improved the constructive constant to ~0.22 * 2^n.

------------------------------------------------------------------------------
DISCIPLINE
------------------------------------------------------------------------------
Every subset-sum, comparison, and search value is an exact Python int.  No
floats occur anywhere in verification or search.  float() is used ONLY when
printing the ratio max(A)/2^n for human-readable reporting.

------------------------------------------------------------------------------
CONTENTS  (matches the four deliverables)
------------------------------------------------------------------------------
  1. is_sum_distinct(A)            exact DSS verifier (+ two independent
                                   cross-check implementations and unit tests)
  2. f_parallel(n) / f_serial(n)   exact f(n) by branch-and-bound, parallelized
                                   over leading-element prefixes
  3. conway_guy(n)                 reconstruct A005318 sets; verify DSS; ratios
  4. cross-check vs A276661        (OEIS-confirmed through n=10)
"""

import sys
import time
import math
import os
import argparse
from itertools import combinations
from concurrent.futures import ProcessPoolExecutor, as_completed


# ============================================================================
# 1. EXACT DSS VERIFIER
# ============================================================================
def is_sum_distinct(A):
    """Return True iff all 2^|A| subset sums of A are pairwise distinct.

    Bitmask frontier: `frontier` is an int whose bit i is 1 iff the value i is
    achievable as a subset sum of the elements processed so far.  Adding an
    element a shifts the whole frontier left by a; a collision (some new sum
    equals an old achievable sum) occurs iff frontier & (frontier << a) != 0.
    Exact big-integer arithmetic; early-exits on the first collision.

    >>> is_sum_distinct([1, 2, 4, 8])
    True
    >>> is_sum_distinct([1, 2, 3])     # 1 + 2 == 3
    False
    """
    frontier = 1  # only the empty-set sum (0) is achievable initially
    for a in A:
        a = int(a)
        if a <= 0:
            raise ValueError("DSS is defined for positive integers")
        shifted = frontier << a
        if frontier & shifted:
            return False
        frontier |= shifted
    return True


def is_sum_distinct_setframe(A):
    """Independent reference impl using an explicit set of achievable sums."""
    sums = {0}
    for a in A:
        a = int(a)
        new = {s + a for s in sums}
        if new & sums:
            return False
        sums |= new
    return True


def is_sum_distinct_bruteforce(A):
    """Independent reference impl: enumerate ALL 2^n subset sums and check the
    number of DISTINCT sums equals 2^n.  Only used to validate the fast paths
    on small inputs (it is exponential in n)."""
    A = [int(a) for a in A]
    n = len(A)
    seen = set()
    for r in range(n + 1):
        for combo in combinations(A, r):
            seen.add(sum(combo))
    return len(seen) == (1 << n)


# ============================================================================
# 3. RECORD CONSTRUCTIONS  (defined early; f(n) uses Conway-Guy as a bound)
# ============================================================================
def conway_guy(n):
    """Conway-Guy construction (OEIS A005318) -> a sum-distinct set of size n.

    Auxiliary sequence u: u(0)=0, u(1)=1, and for k>=2
        u(k) = 2*u(k-1) - u(k-1-r),   r = nearest integer to sqrt(2*(k-1)).
    The order-n set is  S_n = { u(n) - u(n-i) : i = 1..n }, sorted ascending.
    max(S_n) = u(n) = A005318(n).  Verified DSS for all n tested.
    """
    if n <= 0:
        return []
    u = [0, 1]
    while len(u) <= n:
        k = len(u)                       # computing u[k]
        r = round(math.sqrt(2 * (k - 1)))
        u.append(2 * u[k - 1] - u[max(0, k - 1 - r)])
    return sorted(int(u[n] - u[n - i]) for i in range(1, n + 1))


def powers_of_two(n):
    """{1, 2, 4, ..., 2^(n-1)} -- the trivial sum-distinct set, max 2^(n-1)."""
    return [1 << i for i in range(n)]


# ============================================================================
# 2. EXACT f(n) BY BRANCH-AND-BOUND  (serial + parallel)
# ============================================================================
def _search_prefix(n, prefix, bound):
    """Worker: among all size-n strictly-increasing sum-distinct sets that
    START with the sorted tuple `prefix`, find the smallest max(A) that is
    < bound.  Returns (best_max | None, witness | None, nodes_visited).

    Bitmask frontier branch-and-bound:
      * frontier bit i == achievable subset sum i of the chosen elements.
      * the next element x must satisfy frontier & (frontier<<x) == 0 (DSS).
      * elements strictly increase; to beat the current best the max element
        must be <= best-1, which bounds x's range and prunes the tree.
    `bound` is a FIXED upper bound (Conway-Guy max), so workers are independent.
    """
    frontier = 1
    for a in prefix:
        sh = frontier << a
        if frontier & sh:                # prefix itself not sum-distinct
            return (None, None, 0)
        frontier |= sh

    state = {"best": bound, "witness": None, "nodes": 0}

    def dfs(chosen, last, frontier):
        state["nodes"] += 1
        k = len(chosen)
        if k == n:
            if chosen[-1] < state["best"]:
                state["best"] = chosen[-1]
                state["witness"] = list(chosen)
            return
        need = n - k
        cap = state["best"] - 1          # max element must be <= best-1
        hi = cap - (need - 1)            # leave room for `need` increasing elts
        for x in range(last + 1, hi + 1):
            sh = frontier << x
            if frontier & sh:
                continue
            chosen.append(x)
            dfs(chosen, x, frontier | sh)
            chosen.pop()

    dfs(list(prefix), prefix[-1], frontier)
    if state["witness"] is None:
        return (None, None, state["nodes"])
    return (state["best"], state["witness"], state["nodes"])


def _enumerate_prefixes(n, bound, depth):
    """All strictly-increasing length-`depth` prefixes that could start a
    size-n set with max <= bound-1 (no DSS filtering; workers filter)."""
    out = []

    def rec(chosen, last):
        k = len(chosen)
        if k == depth:
            out.append(tuple(chosen))
            return
        need_total = n - k
        hi = (bound - 1) - (need_total - 1)
        for x in range(last + 1, hi + 1):
            chosen.append(x)
            rec(chosen, x)
            chosen.pop()

    rec([], 0)
    return out


def f_serial(n):
    """Exact f(n) in a single process (reference for small n / cross-check)."""
    if n <= 0:
        return 0, []
    if n <= 2:
        return ({1: 1, 2: 2}[n], {1: [1], 2: [1, 2]}[n])
    bound = max(conway_guy(n))
    best, wit, _ = _search_prefix(n, (1,), bound)  # NOTE: only a_1=1 subtree!
    # a_1 need not be 1, so search every a_1 prefix:
    best_overall = bound
    witness_overall = list(conway_guy(n))
    for p in _enumerate_prefixes(n, bound, 1):
        bm, wt, _ = _search_prefix(n, p, best_overall)
        if bm is not None and bm < best_overall:
            best_overall, witness_overall = bm, wt
    return best_overall, witness_overall


def f_parallel(n, workers=None, split_depth=2, verbose=False):
    """Exact f(n) parallelized over leading-element prefixes.

    Returns (f_n, witness, total_nodes, elapsed_seconds).  f(n) is the minimum
    of max(A) over independent prefix-subtrees; bounded above by the Conway-Guy
    max (which is feasible), so the result is exact and a witness always exists.
    """
    t0 = time.time()
    if n <= 0:
        return 0, [], 1, time.time() - t0
    if n <= 2:
        fn, w = ({1: 1, 2: 2}[n], {1: [1], 2: [1, 2]}[n])
        return fn, w, 1, time.time() - t0

    cg = conway_guy(n)
    bound = max(cg)                       # fixed upper bound; f(n) <= bound
    best, best_witness = bound, list(cg)

    # adapt split depth so there are plenty of prefixes for load balance
    d = min(split_depth, n - 1)
    prefixes = _enumerate_prefixes(n, bound, d)
    while len(prefixes) < 4 * (workers or os.cpu_count() or 4) and d < n - 1:
        d += 1
        prefixes = _enumerate_prefixes(n, bound, d)
    if verbose:
        print(f"    [n={n} bound(CG)={bound} split_depth={d} "
              f"#prefixes={len(prefixes)}]", file=sys.stderr, flush=True)

    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 1)

    total_nodes = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_search_prefix, n, p, bound) for p in prefixes]
        for fut in as_completed(futs):
            bm, wt, nodes = fut.result()
            total_nodes += nodes
            if bm is not None and bm < best:
                best, best_witness = bm, wt
    return best, best_witness, total_nodes, time.time() - t0


# ============================================================================
# 4. REFERENCE DATA FOR CROSS-CHECK
# ============================================================================
# OEIS A276661 = f(n), minimal largest element of a sum-distinct set of size n.
# CONFIRMED VALUES: the OEIS b-file currently lists A276661 only through n=10.
A276661_OEIS = {0: 0, 1: 1, 2: 2, 3: 4, 4: 7, 5: 13, 6: 24, 7: 44, 8: 84,
                9: 161, 10: 309}

# A005318 = Conway-Guy max(S_n). Conway-Guy is proven/known optimal (== f(n))
# only for n <= 8 (Lunnon 1988); it is conjectured optimal but is asymptotically
# NOT optimal (Bohman). Numerically A005318 == A276661 at least through n = 11
# (both 594); A005318 then exceeds the best known f(n) for n >= 12.
A005318 = {0: 0, 1: 1, 2: 2, 3: 4, 4: 7, 5: 13, 6: 24, 7: 44, 8: 84, 9: 161,
           10: 309, 11: 594, 12: 1164, 13: 2284, 14: 4484, 15: 8807,
           16: 17305, 17: 34301, 18: 68008, 19: 134852, 20: 267420,
           21: 530356, 22: 1051905, 23: 2095003, 24: 4172701}


# ============================================================================
# DRIVER
# ============================================================================
def run_unit_tests():
    print("=" * 78)
    print("DELIVERABLE 1: exact DSS verifier -- unit tests")
    print("=" * 78)
    tests = [
        ([1, 2, 4, 8], True),
        ([1, 2, 3], False),            # 1 + 2 == 3
        ([1], True),
        ([1, 2, 4], True),
        ([2, 3, 4], True),             # sums 0,2,3,4,5,6,7,9 all distinct
        ([3, 5, 6, 7], True),          # all 16 subset sums distinct
        ([1, 5, 10, 11], False),       # 1 + 10 == 11
        ([2, 3, 5], False),            # 2 + 3 == 5
        ([1, 2, 4, 8, 16], True),
        ([6, 9, 11, 12, 13], True),    # Conway-Guy n=5, max 13
        ([3, 6, 9], False),            # 3 + 6 == 9
    ]
    ok_all = True
    for A, expected in tests:
        fast = is_sum_distinct(A)
        setf = is_sum_distinct_setframe(A)
        brut = is_sum_distinct_bruteforce(A)
        agree = (fast == setf == brut)
        ok = agree and (fast == expected)
        ok_all &= ok
        print(f"  {str(A):>22} -> {str(fast):>5}  "
              f"(setframe={setf}, brute={brut}, expect={expected})  "
              f"{'OK' if ok else 'FAIL'}")
    # also: all Conway-Guy sets up to n=24 are DSS and match A005318
    cg_ok = all(is_sum_distinct(conway_guy(n)) and max(conway_guy(n)) == A005318[n]
                for n in range(1, 25))
    print(f"  Conway-Guy sets n=1..24 all DSS and match A005318: {cg_ok}")
    ok_all &= cg_ok
    print(f"  ALL TESTS: {'PASSED' if ok_all else 'FAILED'}\n")
    return ok_all


def run_constructions(nmax=24):
    print("=" * 78)
    print("DELIVERABLE 3: record constructions -- powers of 2 vs Conway-Guy (A005318)")
    print("=" * 78)
    print(f"{'n':>3} | {'pow2 max':>10} {'/2^n':>7} | {'CG max':>10} {'/2^n':>7} "
          f"{'DSS':>5} | {'CG set (n<=8)':>32}")
    rows = []
    for n in range(1, nmax + 1):
        p2 = powers_of_two(n)
        cg = conway_guy(n)
        twon = 1 << n
        dss = is_sum_distinct(cg)
        rows.append((n, max(p2), max(cg), dss))
        cg_str = str(cg) if n <= 8 else ""
        print(f"{n:>3} | {max(p2):>10} {max(p2)/twon:>7.4f} | "
              f"{max(cg):>10} {max(cg)/twon:>7.4f} {str(dss):>5} | {cg_str:>32}")
    print()
    return rows


def run_exhaustive(nmax, time_budget, per_n_cap, workers, split_depth):
    print("=" * 78)
    print("DELIVERABLE 2 + 4: exhaustive f(n) (exact) with A276661 cross-check")
    print("=" * 78)
    print(f"{'n':>3} | {'f(n)':>7} | {'f/2^n':>8} | {'A276661':>8} {'CG(A005318)':>11} "
          f"{'status':>10} | {'time(s)':>8} | witness")
    t_start = time.time()
    results = {}
    for n in range(1, nmax + 1):
        if time.time() - t_start > time_budget:
            print(f"  [TIME BUDGET {time_budget}s reached; stopping before n={n}]")
            break
        fn, witness, nodes, dt = f_parallel(n, workers=workers,
                                            split_depth=split_depth, verbose=True)
        # self-verify the witness independently (brute force only for small n)
        vok = (len(witness) == n and len(set(witness)) == n
               and max(witness) == fn and is_sum_distinct(witness)
               and is_sum_distinct_setframe(witness))
        if n <= 12:
            vok = vok and is_sum_distinct_bruteforce(witness)
        ref = A276661_OEIS.get(n)
        cg = A005318.get(n)
        if ref is not None:
            status = "OEIS-MATCH" if ref == fn else "OEIS-DIFF!"
        elif cg is not None:
            status = "==CG" if cg == fn else ("<CG" if fn < cg else ">CG?")
        else:
            status = ""
        results[n] = dict(f=fn, witness=witness, nodes=nodes, dt=dt,
                          verified=bool(vok), ref=ref, cg=cg, status=status)
        wstr = str(witness) if n <= 12 else f"max={fn}"
        print(f"{n:>3} | {fn:>7} | {fn/(1<<n):>8.5f} | {str(ref):>8} {str(cg):>11} "
              f"{status:>10} | {dt:>8.2f} | {wstr}  verify={vok}")
        if dt > per_n_cap:
            print(f"  [n={n} took {dt:.0f}s > per-n cap {per_n_cap}s; stopping]")
            break
    total = time.time() - t_start
    print(f"\nTotal exhaustive wall time: {total:.1f}s; "
          f"largest n reached: {max(results) if results else 0}\n")
    return results


def main():
    ap = argparse.ArgumentParser(description="Erdos #1 distinct subset sums study")
    ap.add_argument("--nmax", type=int, default=10,
                    help="max n for exhaustive f(n) (default 10)")
    ap.add_argument("--time-budget", type=float, default=24 * 60,
                    help="total seconds for the exhaustive sweep")
    ap.add_argument("--per-n-cap", type=float, default=15 * 60,
                    help="stop if a single n exceeds this many seconds")
    ap.add_argument("--workers", type=int, default=None,
                    help="process-pool size (default cpu_count-1)")
    ap.add_argument("--split-depth", type=int, default=2,
                    help="prefix length to parallelize over")
    ap.add_argument("--constructions-nmax", type=int, default=24)
    args = ap.parse_args()

    run_unit_tests()
    run_constructions(args.constructions_nmax)
    run_exhaustive(args.nmax, args.time_budget, args.per_n_cap,
                   args.workers, args.split_depth)


if __name__ == "__main__":
    main()
