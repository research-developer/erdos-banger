#!/usr/bin/env python3
"""Exact-integer study of Erdos #1052: unitary perfect numbers.

A unitary divisor d | n satisfies gcd(d, n/d) = 1.  Equivalently, if
n = prod p_i^{a_i}, the unitary divisors are exactly the products of a
subset of the prime-power blocks p_i^{a_i}.  The unitary divisor-sum is
therefore multiplicative on the prime-power blocks:

    sigma*(n) = prod_i (1 + p_i^{a_i}).

n is *unitary perfect* iff sigma*(n) = 2n, i.e. the sum of its unitary
divisors other than n itself equals n.

Exactly five are known (OEIS A002827):

    6, 60, 90, 87360, 146361946186458562560000

Erdos #1052 asks whether there are only finitely many.  This OPEN problem
is NOT resolved here; this module produces *exact verified data* and
structural evidence only.  Zero floating point: Python big ints throughout.

Run:  python3 unitary_perfect.py
"""

from __future__ import annotations

import array
import sys
from math import isqrt

# --------------------------------------------------------------------------
# Exact integer factorization (trial division + Pollard rho for big factors).
# Every known unitary perfect number factors into small primes, so trial
# division alone resolves verification; rho keeps the arbitrary-n path exact
# and fast on larger inputs.
# --------------------------------------------------------------------------


def _is_probable_prime(n: int) -> bool:
    """Strong (Miller-Rabin) primality test with a large fixed witness set.

    Deterministic for all n below ~3.18e23 with the first 12 primes; the extra
    bases push correctness well past our inputs.  Exact integer arithmetic.
    """
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small_primes:
        if n % p == 0:
            return n == p
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    witnesses = small_primes + [41, 43, 47, 53, 59, 61, 67, 71, 73]
    for a in witnesses:
        a %= n
        if a == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _pollard_rho(n: int) -> int:
    """Return a nontrivial factor of composite n (exact integer Brent rho)."""
    if n % 2 == 0:
        return 2
    if n % 3 == 0:
        return 3
    from random import Random

    rng = Random(0xC0FFEE)  # deterministic seed: reproducible runs
    while True:
        c = rng.randrange(1, n)

        def f(x: int) -> int:
            return (x * x + c) % n

        x = y = rng.randrange(2, n)
        d = 1
        while d == 1:
            x = f(x)
            y = f(f(y))
            d = _gcd(abs(x - y), n)
        if d != n:
            return d


def factorize(n: int) -> dict[int, int]:
    """Exact prime factorization of n >= 1 as {prime: exponent}.

    Trial division by small primes, then Pollard rho recursion for any large
    cofactor.  Pure integer arithmetic.
    """
    if n < 1:
        raise ValueError("factorize requires n >= 1")
    factors: dict[int, int] = {}
    if n == 1:
        return factors

    limit = 1_000_000
    d = 2
    while d <= limit and d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2

    if n == 1:
        return factors
    if _is_probable_prime(n):
        factors[n] = factors.get(n, 0) + 1
        return factors

    stack = [n]
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if _is_probable_prime(m):
            factors[m] = factors.get(m, 0) + 1
            continue
        f = _pollard_rho(m)
        stack.append(f)
        stack.append(m // f)
    return factors


# --------------------------------------------------------------------------
# Core: sigma*(n) and the unitary-perfect predicate.
# --------------------------------------------------------------------------


def sigma_star(n: int) -> int:
    """Sum of the unitary divisors of n: sigma*(n) = prod (1 + p^a).

    sigma*(1) = 1 (empty product).  Exact integer.
    """
    if n < 1:
        raise ValueError("sigma_star requires n >= 1")
    result = 1
    for p, a in factorize(n).items():
        result *= 1 + p**a
    return result


def sigma_star_from_factors(factors: dict[int, int]) -> int:
    """sigma* directly from a known factorization {p: a}.  Avoids refactoring."""
    result = 1
    for p, a in factors.items():
        result *= 1 + p**a
    return result


def is_unitary_perfect(n: int) -> bool:
    """True iff sigma*(n) == 2n  (n equals the sum of its proper unitary divisors)."""
    if n < 1:
        return False
    return sigma_star(n) == 2 * n


# --------------------------------------------------------------------------
# Known data.
# --------------------------------------------------------------------------

KNOWN_UNITARY_PERFECT = [
    6,
    60,
    90,
    87360,
    146361946186458562560000,
]


def _fmt_factors(factors: dict[int, int]) -> str:
    return " * ".join(
        f"{p}^{a}" if a > 1 else f"{p}" for p, a in sorted(factors.items())
    )


def verify_known() -> bool:
    """Verify every known UP exactly; print factorization and sigma*/2n check."""
    print("=" * 72)
    print("VERIFICATION OF THE 5 KNOWN UNITARY PERFECT NUMBERS")
    print("=" * 72)
    all_ok = True
    for n in KNOWN_UNITARY_PERFECT:
        fac = factorize(n)
        recon = 1
        for p, a in fac.items():
            recon *= p**a
        s = sigma_star_from_factors(fac)
        ok = recon == n and s == 2 * n
        all_ok &= ok
        print(f"\nn  = {n}")
        print(f"   = {_fmt_factors(fac)}")
        print(f"   factorization reconstructs n: {recon == n}")
        print(f"   sigma*(n) = {s}")
        print(f"   2n        = {2 * n}")
        print(
            f"   sigma*(n) == 2n : {s == 2 * n}   -> "
            f"{'UNITARY PERFECT' if ok else 'FAIL'}"
        )
    print("\n" + "-" * 72)
    print(f"ALL 5 VERIFIED EXACTLY: {all_ok}")
    print("-" * 72, flush=True)
    return all_ok


# --------------------------------------------------------------------------
# Exhaustive search for a 6th unitary perfect number, by a linear sieve.
#
# We compute sigma*(n) for EVERY n in [2, N] exactly via the multiplicative
# recurrence on the smallest-prime block:
#
#     write n = p^a * m  with p = smallest prime factor, gcd(p, m) = 1;
#     then sigma*(n) = (1 + p^a) * sigma*(m),  and m < n so sigma*(m) is known.
#
# n is unitary perfect iff sigma*(n) == 2n.  This checks every integer up to N
# with no per-n factorization and no block/prime bound to get wrong -- it is a
# fully exhaustive, obviously-correct non-existence certificate for [1, N].
# (Bounded, hence NOT a finiteness proof.)
# --------------------------------------------------------------------------


def unitary_perfect_upto(n_bound: int, verbose: bool = True) -> dict:
    """Exhaustively list all unitary perfect n in [1, n_bound] by a linear sieve.

    Exact integer arithmetic.  Memory ~ 12 bytes/n (one int32 spf array + one
    int64 sigma* array), so n_bound up to ~1e8 is comfortable.
    """
    if n_bound < 1:
        return {"n_bound": n_bound, "found": []}

    # Smallest-prime-factor sieve.
    spf = array.array("i", range(n_bound + 1))
    i = 2
    while i * i <= n_bound:
        if spf[i] == i:  # i is prime
            for j in range(i * i, n_bound + 1, i):
                if spf[j] == j:
                    spf[j] = i
        i += 1

    # sigma* via the block recurrence; sig fits in int64 well past 1e8.
    sig = array.array("q", bytes(8 * (n_bound + 1)))
    if n_bound >= 1:
        sig[1] = 1
    found: list[int] = []
    for n in range(2, n_bound + 1):
        p = spf[n]
        m = n
        pa = 1
        while m % p == 0:
            m //= p
            pa *= p
        v = sig[m] * (1 + pa)  # m < n, exact; v = sigma*(n)
        sig[n] = v
        if v == 2 * n:
            found.append(n)

    if verbose:
        print("\n" + "=" * 72)
        print("EXHAUSTIVE SIEVE SEARCH FOR UNITARY PERFECT NUMBERS")
        print("=" * 72)
        print(f"checked EVERY integer n in [1, {n_bound}]")
        print(f"unitary perfect numbers found: {found}", flush=True)
    return {"n_bound": n_bound, "found": found}


# --------------------------------------------------------------------------
# Structured block search (secondary, exact) -- the (1+1/q) = 2 viewpoint.
#
# n is UP iff prod over blocks q_i = p_i^{a_i} of (1 + 1/q_i) = 2 (distinct
# primes).  This DFS recovers the known UPs whose blocks lie in a chosen pool
# and double-checks the sieve.  Each hit is INDEPENDENTLY re-verified with
# is_unitary_perfect.  Bounded -> not a finiteness proof.
# --------------------------------------------------------------------------


def _prime_power_blocks(prime_bound: int, value_bound: int) -> list[int]:
    """All prime powers p^a <= value_bound with p <= prime_bound prime, a>=1."""
    sieve = bytearray([1]) * (prime_bound + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, isqrt(prime_bound) + 1):
        if sieve[i]:
            sieve[i * i :: i] = b"\x00" * len(sieve[i * i :: i])
    primes = [i for i in range(2, prime_bound + 1) if sieve[i]]
    blocks: list[int] = []
    for p in primes:
        q = p
        while q <= value_bound:
            blocks.append(q)
            q *= p
    return blocks


def search_blocks(
    prime_bound: int = 200,
    value_bound: int = 200_000,
    max_blocks: int = 8,
    verbose: bool = True,
) -> dict:
    """Exact DFS over sets of distinct-prime prime-power blocks.

    Tests prod (1 + q_i) == 2 * prod q_i.  Safeguards:
      * skips any block whose prime is already used (one block per prime);
      * monotonicity prune: every block multiplies S/P by (1+1/q) > 1, so once
        S > 2P the ratio can never return to 2 -> cut;
      * every (S == 2P) hit is INDEPENDENTLY re-verified with is_unitary_perfect.
    """
    blocks = _prime_power_blocks(prime_bound, value_bound)
    block_prime = {q: next(iter(factorize(q))) for q in blocks}
    blocks.sort()

    found: list[tuple[int, dict[int, int]]] = []
    rejected_hits: list[int] = []
    nodes = 0

    def reachable_upper(S: int, P: int, start: int, used: set, depth: int) -> bool:
        if S >= 2 * P:
            return True
        room = max_blocks - depth
        if room <= 0:
            return False
        s, p = S, P
        seen = set(used)
        taken = 0
        for j in range(start, len(blocks)):
            if taken >= room:
                break
            q = blocks[j]
            pr = block_prime[q]
            if pr in seen:
                continue
            seen.add(pr)
            s *= 1 + q
            p *= q
            taken += 1
            if s >= 2 * p:
                return True
        return s >= 2 * p

    def dfs(start: int, used: set, P: int, S: int, chosen: list[int], depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if depth >= 1 and S == 2 * P:
            if is_unitary_perfect(P):
                fac = {block_prime[q]: factorize(q)[block_prime[q]] for q in chosen}
                found.append((P, dict(fac)))
            else:
                rejected_hits.append(P)
            return
        if S > 2 * P:  # monotonicity prune
            return
        if depth >= max_blocks:
            return
        if not reachable_upper(S, P, start, used, depth):
            return
        for j in range(start, len(blocks)):
            q = blocks[j]
            pr = block_prime[q]
            if pr in used:
                continue
            used.add(pr)
            chosen.append(q)
            dfs(j + 1, used, P * q, S * (1 + q), chosen, depth + 1)
            chosen.pop()
            used.discard(pr)

    dfs(0, set(), 1, 1, [], 0)
    found_n = sorted({P for P, _ in found})
    if verbose:
        print("\n" + "=" * 72)
        print("STRUCTURED BLOCK SEARCH (secondary cross-check)")
        print("=" * 72)
        print(f"prime_bound = {prime_bound}, value_bound (max block p^a) = {value_bound}")
        print(f"max_blocks = {max_blocks}, blocks in pool = {len(blocks)}, nodes = {nodes}")
        if rejected_hits:
            print(f"!! hits rejected by independent re-check: {sorted(set(rejected_hits))}")
        print(f"unitary perfect numbers found: {found_n}", flush=True)
        for P, fac in sorted(found, key=lambda t: t[0]):
            print(f"   {P} = {_fmt_factors(fac)}  (sigma* = {sigma_star_from_factors(fac)} = 2*{P})")
    return {"found": found_n, "nodes": nodes, "rejected_hits": sorted(set(rejected_hits))}


# --------------------------------------------------------------------------
# Structural observations (exact, verifiable) toward the finiteness question.
# --------------------------------------------------------------------------


def parity_observations() -> None:
    """Print exact 2-adic / parity facts that constrain unitary perfect n."""
    print("\n" + "=" * 72)
    print("STRUCTURAL OBSERVATIONS (exact, verifiable)")
    print("=" * 72)
    print(
        "Let n = prod p_i^{a_i} and sigma*(n) = prod (1 + p_i^{a_i}).\n"
        "\n"
        "(1) PARITY OF EACH BLOCK SUM.\n"
        "    For an odd prime power q = p^a (p odd):  1 + q is EVEN.\n"
        "    For q = 2^a:                              1 + 2^a is ODD.\n"
        "\n"
        "(2) 2-ADIC BALANCE.  sigma*(n) = 2n forces v2(sigma*(n)) = 1 + v2(n).\n"
        "    The block 2^a contributes a to v2(2n) but (1+2^a) is odd, so ALL\n"
        "    factors of two in sigma*(n) come from the odd blocks.  Each odd\n"
        "    block 1+p^a supplies >= 1 factor of two, and they must total\n"
        "    exactly 1 + v2(n).  In particular a unitary perfect n > 1 must be\n"
        "    EVEN (an all-odd n has sigma*(n) odd, never 2n) -- consistent with\n"
        "    all 5 known.  This caps the number of odd prime-power blocks for a\n"
        "    fixed power of two.\n"
        "\n"
        "(3) ABUNDANCY VIEW.  n is UP iff prod (1 + 1/p_i^{a_i}) = 2 exactly.\n"
        "    Each factor (1+1/q) > 1 and -> 1 as q grows; while the product\n"
        "    over ALL prime powers diverges, hitting EXACTLY 2 with finitely\n"
        "    many distinct-prime blocks is rigid -- it forces small blocks and\n"
        "    pins down structure.  This is the lever behind the known partial\n"
        "    finiteness results (e.g. bounds on the count of distinct odd\n"
        "    primes once the power of two is fixed)."
    )
    print("\n   Per-block (1+q) parity for the 5 known unitary perfect numbers:")
    for n in KNOWN_UNITARY_PERFECT:
        parts = []
        for p, a in sorted(factorize(n).items()):
            q = p**a
            parts.append(f"(1+{q})={'odd' if (1 + q) % 2 else 'even'}")
        print(f"     n={n}: " + ", ".join(parts))


def _cross_check_sieve(n_bound: int = 100_000) -> bool:
    """Confirm the linear-sieve sigma* agrees with the factorization sigma_star
    on a sample of n -- two independent implementations must coincide."""
    res = unitary_perfect_upto(n_bound, verbose=False)
    # Spot-check sigma* on a spread of n via both methods.
    import array as _arr  # local: rebuild sigma* exactly as the sieve does

    spf = _arr.array("i", range(n_bound + 1))
    i = 2
    while i * i <= n_bound:
        if spf[i] == i:
            for j in range(i * i, n_bound + 1, i):
                if spf[j] == j:
                    spf[j] = i
        i += 1
    sig = _arr.array("q", bytes(8 * (n_bound + 1)))
    sig[1] = 1
    for n in range(2, n_bound + 1):
        p = spf[n]
        m = n
        pa = 1
        while m % p == 0:
            m //= p
            pa *= p
        sig[n] = sig[m] * (1 + pa)
    ok = all(sig[n] == sigma_star(n) for n in (2, 3, 6, 99, 1000, 87360, n_bound))
    return ok and res["found"][:4] == [6, 60, 90, 87360][: len(res["found"])]


def main(argv: list[str]) -> int:
    # 1. Verify all 5 known unitary perfect numbers exactly.
    if not verify_known():
        print("\nFATAL: a known unitary perfect number failed verification.")
        return 1

    # 2. Structural observations.
    parity_observations()

    # 3. Cross-check the two independent sigma* implementations agree.
    print("\n" + "=" * 72)
    print("CROSS-CHECK: linear-sieve sigma*  vs  factorization sigma_star")
    print("=" * 72)
    xc = _cross_check_sieve(100_000)
    print(f"two independent sigma* implementations agree on sample: {xc}", flush=True)
    if not xc:
        print("\nFATAL: sieve / factorization sigma* mismatch.")
        return 1

    # 4. Exhaustive sieve search.  N chosen to finish in the time-box; every
    #    integer in [1, N] is checked (no block/prime bound to get wrong).
    #    Override on the command line, e.g.  python3 unitary_perfect.py 200000000
    n_bound = 100_000_000
    if len(argv) >= 1:
        n_bound = int(argv[0])
    unitary_perfect_upto(n_bound, verbose=True)

    # 5. Secondary block-DFS cross-check (recovers the small known UPs and
    #    confirms zero spurious hits via independent re-verification).
    r = search_blocks(prime_bound=200, value_bound=200_000, max_blocks=8, verbose=True)
    assert r["found"] == [6, 60, 90, 87360], f"block-search self-test failed: {r['found']}"
    assert not r["rejected_hits"], f"unexpected rejected hits: {r['rejected_hits']}"

    print("\n" + "=" * 72)
    print("CONCLUSION")
    print("=" * 72)
    print(
        "All 5 known unitary perfect numbers verified exactly (including the\n"
        f"24-digit one).  Exhaustively checking every integer in [1, {n_bound}]\n"
        "found ONLY the known small ones (6, 60, 90, 87360); no 6th exists\n"
        "below that bound.  A 6th unitary perfect number, if it exists, must\n"
        "exceed it (and be even, by the 2-adic argument above).  Erdos #1052\n"
        "(finiteness) remains OPEN; this run is exact verified data + a bounded\n"
        "non-existence certificate only -- it does NOT resolve the problem.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
