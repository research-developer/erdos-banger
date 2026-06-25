#!/usr/bin/env python3
"""Exact-integer computational study of Erdos #470 (weird numbers).

Zero-float / exact integer discipline throughout:
  - sigma(n) and proper-divisor lists come from integer factorization (sympy.factorint).
  - "pseudoperfect" is decided by an EXACT subset-sum over the proper divisors
    (a Python-int bitset DP; no floats, no probabilistic shortcuts).

Definitions (Erdos #470 / OEIS A006037, A002975):
  abundant         : sigma(n) >= 2n           (proper-divisor sum s(n) = sigma(n) - n >= n)
  pseudoperfect    : some subset of the proper divisors sums to n  (a.k.a. semiperfect)
  weird            : abundant AND NOT pseudoperfect
  primitive weird  : weird and NONE of its proper divisors is weird

This script is a verification/evidence tool for an OPEN problem.
It does NOT claim to resolve #470. It produces exact, reproducible data.
"""
from __future__ import annotations

import argparse
import array
import os
import time
from typing import Iterable

from sympy import factorint


# ---------------------------------------------------------------------------
# Exact arithmetic primitives
# ---------------------------------------------------------------------------
def sigma(n: int) -> int:
    """Sum of ALL positive divisors of n (including n), exact via factorization.

    sigma(prod p_i^a_i) = prod (p_i^(a_i+1) - 1)/(p_i - 1), computed in Z.
    """
    if n <= 0:
        raise ValueError("sigma defined for n >= 1")
    total = 1
    for p, a in factorint(n).items():
        # (p^(a+1) - 1) // (p - 1) is an exact integer (geometric series).
        total *= (p ** (a + 1) - 1) // (p - 1)
    return total


def proper_divisors(n: int) -> list[int]:
    """All positive divisors of n strictly less than n (excludes n, includes 1)."""
    if n <= 0:
        raise ValueError("proper_divisors defined for n >= 1")
    facs = factorint(n)
    divs = [1]
    for p, a in facs.items():
        divs = [d * (p ** e) for d in divs for e in range(a + 1)]
    divs = [d for d in divs if d != n]
    divs.sort()
    return divs


def is_abundant(n: int) -> bool:
    """sigma(n) >= 2n  <=>  proper-divisor sum >= n."""
    return sigma(n) >= 2 * n


def subset_sum_reaches(divisors: Iterable[int], target: int) -> bool:
    """EXACT decision: does some subset of `divisors` sum to exactly `target`?

    Bitset DP over arbitrary-precision Python ints. Bit i of `reachable`
    is set iff some subset sums to i. Updating with a divisor d is a single
    shift-or: reachable |= reachable << d, masked to [0, target].

    This is exact (no float, no randomness) and far faster than enumerating
    2^k subsets. Pruning: drop divisors > target; if running sum < target it
    can never reach target.
    """
    divs = sorted(d for d in divisors if 0 < d <= target)
    if target == 0:
        return True
    if sum(divs) < target:
        return False
    mask = (1 << (target + 1)) - 1
    reachable = 1  # bit 0 set: empty subset sums to 0
    target_bit = 1 << target
    for d in divs:
        reachable |= (reachable << d)
        reachable &= mask
        if reachable & target_bit:
            return True
    return bool(reachable & target_bit)


def divisors_hit_target(divs: list[int], target: int, total: int) -> bool:
    """EXACT: does some subset of `divs` (summing to `total`) hit `target`?

    Complement optimization: a subset sums to `target` iff its complement sums
    to `total - target`. Both are equivalent decisions, so we run the bitset DP
    toward whichever is SMALLER. For barely-abundant numbers (the common case,
    especially among odd numbers) `total - target` is tiny, making the DP word
    count O((total-target)/64) instead of O(target/64) -- orders of magnitude
    cheaper while remaining a fully exact integer computation.
    """
    if target < 0 or target > total:
        return False
    goal = min(target, total - target)
    return subset_sum_reaches(divs, goal)


def is_pseudoperfect(n: int, divs: list[int] | None = None) -> bool:
    """Some subset of the PROPER divisors of n sums to n (exact)."""
    if divs is None:
        divs = proper_divisors(n)
    return divisors_hit_target(divs, n, sum(divs))


def is_weird(n: int) -> bool:
    """weird = abundant AND NOT pseudoperfect."""
    if n <= 0:
        return False
    divs = proper_divisors(n)
    s = sum(divs)              # proper-divisor sum = sigma(n) - n
    if s < n:                  # deficient or perfect -> not abundant
        return False
    # abundant; weird iff no subset of proper divisors hits n exactly.
    return not divisors_hit_target(divs, n, s)


# ---------------------------------------------------------------------------
# Searches
# ---------------------------------------------------------------------------
def find_weird_numbers(limit: int) -> list[int]:
    """All weird n with 1 <= n <= limit (both parities)."""
    out = []
    for n in range(2, limit + 1):
        if is_weird(n):
            out.append(n)
    return out


def sigma_sieve(limit: int) -> "array.array":
    """Sieve s[n] = sum of ALL divisors of n (sigma(n)) for n in [0, limit].

    Exact integer divisor-sum sieve: for each d, add d to every multiple of d.
    O(limit log limit) additions, all integer. Returns an array of unsigned
    64-bit ints (sigma(n) < ~ n * log log n, well within 64 bits for our range).
    """
    s = array.array("Q", [0]) * (limit + 1)
    for d in range(1, limit + 1):
        for m in range(d, limit + 1, d):
            s[m] += d
    return s


def odd_weird_search(limit: int, report_every: int = 0,
                     block: int = 10_000_000) -> tuple[int, list[int]]:
    """Scan ODD n up to `limit` for weird numbers. Returns (bound, found).

    Two-phase exact pipeline:
      1. Sieve sigma over a block (no per-number factorization). An odd n is a
         candidate only if abundant: sigma(n) >= 2n  (equivalently the proper-
         divisor sum sigma(n)-n >= n). Odd abundant numbers are rare (~0.2% of
         odds; smallest is 945), so very few survive.
      2. For each odd abundant candidate, materialize its proper divisors and
         run the complement-optimized EXACT subset-sum. weird iff no subset
         hits n. (Abundance for odds is typically small, so the complement
         target sigma(n)-2n is tiny and the DP is cheap.)

    Blocked to bound sieve memory. Reports progress per block.
    """
    found = []
    bound = 1
    abundant_count = 0
    t0 = time.time()
    lo = 3
    while lo <= limit:
        hi = min(lo + block - 1, limit)
        sig = sigma_sieve(hi)            # sigma[0..hi]
        for n in range(lo | 1, hi + 1, 2):   # odd n in [lo, hi]
            bound = n
            two_n = 2 * n
            if sig[n] < two_n:           # not abundant -> skip (cheap)
                continue
            abundant_count += 1
            divs = proper_divisors(n)    # only for the rare abundant odds
            total = sig[n] - n           # proper-divisor sum
            if not divisors_hit_target(divs, n, total):
                found.append(n)
                print(f"  !! ODD WEIRD FOUND: {n}", flush=True)
        if report_every:
            el = time.time() - t0
            print(f"  [odd] scanned to n={hi:,}  "
                  f"({el:.1f}s, {abundant_count:,} odd-abundant, "
                  f"{len(found)} weird)", flush=True)
        lo = hi + 1
    return bound, found


def primitive_weird_numbers(limit: int) -> tuple[list[int], list[int]]:
    """Return (weird_list, primitive_weird_list) for n <= limit.

    A weird number is PRIMITIVE if none of its proper divisors is weird.
    We compute the full weird set first, then filter.
    """
    weird = find_weird_numbers(limit)
    weird_set = set(weird)
    primitive = []
    for w in weird:
        if not any(d in weird_set for d in proper_divisors(w)):
            primitive.append(w)
    return weird, primitive


# ---------------------------------------------------------------------------
# Self-tests (unit tests required by the brief)
# ---------------------------------------------------------------------------
def run_unit_tests() -> None:
    print("== unit tests ==", flush=True)

    # sigma sanity
    assert sigma(1) == 1
    assert sigma(6) == 12          # perfect: 1+2+3+6
    assert sigma(12) == 28         # 1+2+3+4+6+12
    assert sigma(70) == 144        # 1+2+5+7+10+14+35+70
    assert sigma(28) == 56         # perfect

    # proper divisors
    assert proper_divisors(70) == [1, 2, 5, 7, 10, 14, 35]
    assert proper_divisors(12) == [1, 2, 3, 4, 6]
    assert sum(proper_divisors(70)) == 74    # abundant (74 > 70)

    # abundance: brief defines abundant as sigma(n) >= 2n (NON-strict),
    # so perfect numbers count as abundant here. (Under either the strict or
    # non-strict convention the WEIRD set is identical, because every perfect
    # number is pseudoperfect and therefore never weird -- verified below.)
    assert is_abundant(12) is True
    assert is_abundant(70) is True
    assert is_abundant(8) is False           # 1+2+4 = 7 < 8 (deficient)
    assert is_abundant(6) is True            # perfect: sigma(6)=12=2*6 -> >=2n
    assert is_abundant(7) is False           # prime, deficient

    # 70 is weird; 12 is abundant but pseudoperfect (1+2+3+6=12)
    assert is_weird(70) is True, "70 must be weird (smallest weird)"
    assert is_weird(12) is False, "12 is pseudoperfect -> not weird"
    assert is_pseudoperfect(12) is True
    assert subset_sum_reaches([1, 2, 3, 4, 6], 12) is True   # 2+4+6 or 1+2+3+6
    # 70's proper divisors have NO subset summing to 70:
    assert subset_sum_reaches([1, 2, 5, 7, 10, 14, 35], 70) is False
    assert is_pseudoperfect(70) is False

    # perfect numbers are pseudoperfect (and not abundant) -> not weird
    assert is_weird(6) is False
    assert is_weird(28) is False

    print("  all unit tests PASSED", flush=True)


# OEIS A006037: weird numbers (reference prefix; the full sequence continues).
OEIS_A006037 = [70, 836, 4030, 5830, 7192, 7912, 9272, 10430, 10570, 10792,
                10990, 11410, 11690, 12110, 12530, 12670, 13370, 13510, 13790,
                13930, 14770, 15610, 15890, 16030, 16310, 16730, 16870, 17272,
                17570, 17990, 18410, 18830, 18970, 19390, 19670, 19810]

# OEIS A002975: primitive weird numbers
OEIS_A002975 = [70, 836, 4030, 5830, 7192, 7912, 9272, 10792, 17272, 45356,
                73616, 83312, 91388, 113072, 243892, 254012, 338572, 343876,
                388076, 519712, 539744, 555616, 682592, 786208, 1188256,
                1229152, 1713592, 1901728, 2081824, 2189024, 3963968, 4128448]


def load_bfile(path: str) -> list[int] | None:
    """Parse an OEIS b-file ('# comments' + lines 'index value'). None if absent."""
    if not path or not os.path.exists(path):
        return None
    vals = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                vals.append(int(parts[1]))
    return vals or None


def _prefix_agrees(computed: list[int], reference: list[int]) -> bool:
    """Element-wise agreement over the overlap of computed and reference.

    The reference arrays are finite prefixes of the (infinite) OEIS sequences,
    and the search range may extend beyond or fall short of them. The correct
    check is that wherever both are defined they agree exactly -- i.e. the two
    sorted lists share a common prefix up to min(len) terms.
    """
    k = min(len(computed), len(reference))
    return computed[:k] == reference[:k]


def _check_one(name: str, computed: list[int], reference: list[int],
               limit: int, from_bfile: bool) -> bool:
    """Compare a computed sequence against an OEIS reference within range.

    Within min(limit, reference_max) the computed set must equal the reference
    set EXACTLY (every term, both directions) -- this catches both false
    positives (extra weird numbers) and false negatives (missed ones).
    """
    ref_max = reference[-1]
    cmp_limit = min(limit, ref_max)
    exp = [x for x in reference if x <= cmp_limit]
    got = [x for x in computed if x <= cmp_limit]
    ok = (got == exp)
    src = "b-file" if from_bfile else "hardcoded-prefix"
    print(f"  {name} <= {cmp_limit:,} [{src}]: "
          f"{'MATCH' if ok else 'MISMATCH'} "
          f"(computed {len(got)}, OEIS {len(exp)})", flush=True)
    if not ok:
        # show first divergence
        for i in range(max(len(got), len(exp))):
            g = got[i] if i < len(got) else None
            e = exp[i] if i < len(exp) else None
            if g != e:
                print(f"    first divergence at index {i}: computed={g} OEIS={e}",
                      flush=True)
                break
    return ok


def verify_against_oeis(weird: list[int], primitive: list[int], limit: int,
                        bfile_weird: list[int] | None = None,
                        bfile_prim: list[int] | None = None) -> None:
    print("== OEIS cross-checks ==", flush=True)
    ref_w = bfile_weird if bfile_weird else OEIS_A006037
    ref_p = bfile_prim if bfile_prim else OEIS_A002975
    ok_w = _check_one("A006037 (weird)", weird, ref_w, limit,
                      from_bfile=bool(bfile_weird))
    ok_p = _check_one("A002975 (primitive)", primitive, ref_p, limit,
                      from_bfile=bool(bfile_prim))
    assert ok_w and ok_p, "OEIS cross-check failed"


def report_primitive_growth(primitive: list[int]) -> None:
    """Decade-by-decade primitive-weird counts (evidence bearing on part (b))."""
    if not primitive:
        return
    print("  primitive-weird growth by decade (count with n < 10^k):", flush=True)
    k = 2
    while 10 ** k <= primitive[-1] * 10:
        c = sum(1 for x in primitive if x < 10 ** k)
        if c:
            print(f"    n < 10^{k:<2}: {c}", flush=True)
        k += 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Erdos #470 weird-number study")
    ap.add_argument("--weird-limit", type=int, default=20000,
                    help="upper bound for weird/primitive enumeration")
    ap.add_argument("--odd-limit", type=int, default=2_000_000,
                    help="upper bound for the odd-weird scan")
    ap.add_argument("--odd-report-every", type=int, default=200_000,
                    help="if nonzero, print a progress line after each sieve block")
    ap.add_argument("--odd-block", type=int, default=10_000_000,
                    help="sieve block size for the odd scan (bounds memory)")
    ap.add_argument("--skip-odd", action="store_true")
    ap.add_argument("--skip-weird", action="store_true",
                    help="skip weird/primitive enumeration (odd scan only)")
    ap.add_argument("--bfile-weird", default="",
                    help="path to OEIS A006037 b-file for full cross-check")
    ap.add_argument("--bfile-prim", default="",
                    help="path to OEIS A002975 b-file for full cross-check")
    ap.add_argument("--dump-weird", default="",
                    help="write computed weird numbers (one per line) to this path")
    ap.add_argument("--dump-prim", default="",
                    help="write computed primitive weird numbers to this path")
    args = ap.parse_args()

    run_unit_tests()

    if not args.skip_weird:
        bf_w = load_bfile(args.bfile_weird)
        bf_p = load_bfile(args.bfile_prim)
        print(f"\n== weird / primitive enumeration up to {args.weird_limit:,} ==",
              flush=True)
        t0 = time.time()
        weird, primitive = primitive_weird_numbers(args.weird_limit)
        el = time.time() - t0
        print(f"  weird count:     {len(weird)}  (in {el:.1f}s)", flush=True)
        print(f"  primitive count: {len(primitive)}", flush=True)
        print(f"  first weird:     {weird[:12]}", flush=True)
        print(f"  first primitive: {primitive[:12]}", flush=True)
        if primitive:
            print(f"  largest primitive in range: {primitive[-1]:,}", flush=True)
        report_primitive_growth(primitive)

        verify_against_oeis(weird, primitive, args.weird_limit,
                            bfile_weird=bf_w, bfile_prim=bf_p)

        if args.dump_weird:
            with open(args.dump_weird, "w") as fh:
                fh.write("\n".join(map(str, weird)) + "\n")
            print(f"  wrote {len(weird)} weird numbers -> {args.dump_weird}",
                  flush=True)
        if args.dump_prim:
            with open(args.dump_prim, "w") as fh:
                fh.write("\n".join(map(str, primitive)) + "\n")
            print(f"  wrote {len(primitive)} primitive numbers -> {args.dump_prim}",
                  flush=True)

    if not args.skip_odd:
        print(f"\n== odd-weird scan up to {args.odd_limit:,} ==", flush=True)
        t0 = time.time()
        bound, odd_found = odd_weird_search(args.odd_limit,
                                            report_every=args.odd_report_every,
                                            block=args.odd_block)
        el = time.time() - t0
        print(f"  odd scan bound reached: {bound:,}  ({el:.1f}s)", flush=True)
        if odd_found:
            print(f"  ODD WEIRD NUMBERS FOUND: {odd_found}", flush=True)
        else:
            print(f"  NO odd weird numbers found in odd [3, {bound:,}]", flush=True)


if __name__ == "__main__":
    main()
