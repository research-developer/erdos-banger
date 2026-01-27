#!/usr/bin/env python3
"""Verify finite counterexamples referenced in CANDIDATES.md.

This is intentionally lightweight and self-contained so it can be run anywhere:
    uv run python scripts/verify_counterexample_candidates.py

Exit codes:
  0: All checks passed
  1: At least one check failed
"""

from __future__ import annotations

import itertools
import math
import sys


class CheckFailed(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def _check_problem_399() -> None:
    """Erdős Problem #399: 10! = 48^4 - 36^4."""
    lhs = math.factorial(10)
    rhs = 48**4 - 36**4
    _require(lhs == rhs, f"Expected 10! == 48^4 - 36^4, got {lhs} != {rhs}")


def _check_problem_649() -> None:
    """Erdős Problem #649 obstruction: 2^k ≢ -1 (mod 7) for all k."""
    # 2 has order 3 mod 7 => residues are {1,2,4}; never 6 (-1 mod 7).
    residues = {pow(2, k, 7) for k in range(0, 21)}
    _require(6 not in residues, f"Unexpected residue 6 in {sorted(residues)}")


def _has_abelian_square(word: str) -> bool:
    """Return True iff `word` contains an abelian square as consecutive blocks."""

    def _counts(block: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for ch in block:
            counts[ch] = counts.get(ch, 0) + 1
        return counts

    n = len(word)
    for start in range(n):
        for length in range(1, (n - start) // 2 + 1):
            a = word[start : start + length]
            b = word[start + length : start + 2 * length]
            if _counts(a) == _counts(b):
                return True
    return False


def _check_problem_231() -> None:
    """Erdős Problem #231: k=4 counterexample word of length 2^4-1 = 15."""
    word = "121312141213121"
    _require(len(word) == 15, f"Expected length 15, got {len(word)}")
    _require(set(word) <= {"1", "2", "3", "4"}, f"Unexpected alphabet: {set(word)}")
    _require(not _has_abelian_square(word), "Word contains an abelian square")


def _check_problem_794() -> None:
    """Erdős Problem #794: n=3 (9 vertices) explicit 28-edge 3-uniform hypergraph."""
    vertices = list(range(1, 10))
    part_a = [1, 2, 3]
    part_b = [4, 5, 6]
    part_c = [7, 8, 9]

    edges: set[tuple[int, int, int]] = set()
    for a in part_a:
        for b in part_b:
            for c in part_c:
                edges.add((a, b, c))
    edges.add((1, 2, 3))
    _require(len(edges) == 28, f"Expected 28 edges, got {len(edges)}")

    def induced_edge_count(subset: tuple[int, ...]) -> int:
        s = set(subset)
        return sum(1 for e in edges if set(e) <= s)

    # Forbidden configurations: a 4-vertex induced subhypergraph with >=3 edges,
    # or a 5-vertex induced subhypergraph with >=7 edges.
    for subset in itertools.combinations(vertices, 4):
        _require(induced_edge_count(subset) < 3, f"Bad 4-set: {subset}")
    for subset in itertools.combinations(vertices, 5):
        _require(induced_edge_count(subset) < 7, f"Bad 5-set: {subset}")


def main() -> int:
    checks = [
        ("#399", _check_problem_399),
        ("#649", _check_problem_649),
        ("#231", _check_problem_231),
        ("#794", _check_problem_794),
    ]

    failures: list[str] = []
    for name, fn in checks:
        try:
            fn()
        except CheckFailed as exc:
            failures.append(f"{name}: {exc}")
        except Exception as exc:
            failures.append(f"{name}: Unexpected {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1

    print("OK all counterexample checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
