"""
Specker graphs (Erdos-Hajnal-Szemeredi 1982, Def. 1.2) as candidates for Problem #74.

We focus on the smallest nontrivial Specker graph:
  G1(n, 3, 1) on 3-subsets of [n].

If X = {x0<x1<x2} and Y = {y0<y1<y2}, then (in the paper's notation) {X,Y} is an edge
iff (after orienting so max(X) < max(Y)):
  x1 < y0 < x2 < y1.

This family has unbounded chromatic number as n→∞ (EHS82 Lemma 1.1(b)).

Goal of this script: Monte Carlo search for an induced subset S with
  ebip(G[S]) > floor(sqrt |S|),
using exact MaxCut (Gray-code) for |S| <= ~25.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random

from ebip_utils import (
    Graph,
    chromatic_number_exact,
    ebip,
    induced_subgraph_edges,
    normalize_edges,
    sqrt_bound,
)


SPECKER_G1_13_3_1_K20_WITNESS: list[int] = [
    1,
    4,
    7,
    69,
    81,
    131,
    135,
    138,
    145,
    153,
    155,
    163,
    189,
    205,
    238,
    240,
    244,
    250,
    274,
    281,
]


def triples(n: int) -> list[tuple[int, int, int]]:
    vs: list[tuple[int, int, int]] = []
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                vs.append((a, b, c))
    return vs


def specker_g1_3_1(n: int) -> tuple[Graph, list[tuple[int, int, int]]]:
    """
    Build G1(n,3,1).

    Vertices: all triples (a<b<c) from [n].
    Edge {X,Y}: if, letting X be the triple with smaller max element,
      X[1] < Y[0] < X[2] < Y[1].
    """

    vs = triples(n)
    edges: list[tuple[int, int]] = []
    for i, x in enumerate(vs):
        for j in range(i + 1, len(vs)):
            y = vs[j]
            if x[2] == y[2]:
                continue
            small, large = (x, y) if x[2] < y[2] else (y, x)
            if small[1] < large[0] < small[2] < large[1]:
                edges.append((i, j))
    g = Graph(len(vs), normalize_edges(len(vs), edges))
    return g, vs


def adjacency_list(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def connected_components(n: int, adj: list[list[int]]) -> list[list[int]]:
    comps: list[list[int]] = []
    seen = [False] * n
    for s in range(n):
        if seen[s]:
            continue
        stack = [s]
        seen[s] = True
        comp: list[int] = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        comps.append(comp)
    return comps


def sample_connected_subset(
    rng: Random, comps: list[list[int]], adj: list[list[int]], k: int
) -> list[int]:
    candidates = [c for c in comps if len(c) >= k]
    if not candidates:
        raise ValueError(f"no connected component with size >= {k}")
    comp = rng.choice(candidates)
    start = rng.choice(comp)
    subset: list[int] = [start]
    in_subset = {start}
    frontier: list[int] = [v for v in adj[start] if v not in in_subset]

    while len(subset) < k:
        if not frontier:
            raise AssertionError("frontier unexpectedly empty")
        v = frontier.pop(rng.randrange(len(frontier)))
        if v in in_subset:
            continue
        in_subset.add(v)
        subset.append(v)
        for w in adj[v]:
            if w not in in_subset:
                frontier.append(w)
    return subset


@dataclass(frozen=True)
class Config:
    n: int = 13  # base parameter
    subset_sizes: tuple[int, ...] = (12, 14, 16, 18, 20, 22, 25)
    samples_per_k: int = 120
    connected_samples_per_k: int = 160
    maxcut_samples_per_k: int = 30
    seed: int = 0


def try_known_witness(cfg: Config, g: Graph, vs: list[tuple[int, int, int]]) -> bool:
    """
    Deterministic check for a known strict √n counterexample.

    Returns True if a violation is confirmed.
    """

    if cfg.n != 13:
        return False
    witness_subset = SPECKER_G1_13_3_1_K20_WITNESS
    k = len(witness_subset)
    sub_edges = induced_subgraph_edges(g.edges, witness_subset)
    e = ebip(k, sub_edges)
    bound = sqrt_bound(k)
    print(f"Known witness check (n=13): k={k} ebip={e} floor(sqrt k)={bound}")
    print(f"  subset triples={[{'v': v, 'triple': vs[v]} for v in witness_subset]}")
    if e > bound:
        print("  -> VIOLATION (Specker G1(13,3,1) fails strict √n)")
        return True
    print("  -> (unexpected) witness did not violate; check implementation")
    print("")
    return False


def main() -> int:
    cfg = Config()
    rng = Random(cfg.seed)  # noqa: S311

    g, vs = specker_g1_3_1(cfg.n)
    adj = adjacency_list(g.n, g.edges)
    comps = connected_components(g.n, adj)

    print("Specker graph test (EHS82 G1(n,3,1))")
    print(f"  n={cfg.n} |V|=C(n,3)={g.n} |E|={g.m}")
    print("")

    if try_known_witness(cfg, g, vs):
        return 1

    violated = False

    for k in cfg.subset_sizes:
        if k > g.n:
            continue

        worst_eb = -1
        worst_subset: list[int] | None = None

        # Uniform samples.
        for j in range(cfg.samples_per_k):
            subset = rng.sample(range(g.n), k)
            if j < cfg.maxcut_samples_per_k:
                sub_edges = induced_subgraph_edges(g.edges, subset)
                e = ebip(k, sub_edges)
                if e > worst_eb:
                    worst_eb = e
                    worst_subset = subset

        # Connected samples (more cycles).
        for j in range(cfg.connected_samples_per_k):
            subset = sample_connected_subset(rng, comps, adj, k)
            if j < cfg.maxcut_samples_per_k:
                sub_edges = induced_subgraph_edges(g.edges, subset)
                e = ebip(k, sub_edges)
                if e > worst_eb:
                    worst_eb = e
                    worst_subset = subset

        ratio = worst_eb / sqrt(k) if worst_eb >= 0 else 0.0
        print(
            f"  k={k:2d}: worst_ebip={worst_eb:2d} "
            f"(sqrt(k)≈{sqrt(k):.2f}, floor(sqrt k)={sqrt_bound(k)}, ratio={ratio:.2f})"
        )

        if worst_eb > sqrt_bound(k):
            violated = True
            subset_sorted = sorted(worst_subset or [])
            sub_edges = induced_subgraph_edges(g.edges, subset_sorted)
            chi = chromatic_number_exact(k, sub_edges)
            decoded = [{"v": v, "triple": vs[v]} for v in subset_sorted]
            print(
                f"    VIOLATION: ebip={worst_eb} > floor(sqrt {k})={sqrt_bound(k)}; "
                f"chi(subset)={chi}"
            )
            print(f"    subset vertices: {decoded}")
            break

    print("")
    print(f"Any sampled violation of the strict √n bound? {violated}")
    return 1 if violated else 0


if __name__ == "__main__":
    raise SystemExit(main())
