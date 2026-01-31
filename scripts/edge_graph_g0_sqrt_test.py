"""
EHS82 "edge graphs" G0(n,k,i) as candidates for Problem #74.

We test the smallest nontrivial iterate beyond the shift graph:
  G0(n, 3, 1) on 3-subsets of [n].

Definition (EHS82 Def. 1.1 specialized):
  Vertices are triples X = {x0<x1<x2}.
  The edge condition for i=1 is (informally) a "shift":
    {X,Y} is an edge if Y starts where X's middle is, or vice-versa.

We implement a symmetric version consistent with the k=2 ordered-edge (shift) rule:
  Adjacent iff  X[1] == Y[0]  OR  Y[1] == X[0].

Goal: Monte Carlo search for a strict √n violation on induced subgraphs
(exact MaxCut for |S| <= ~25).
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


def triples(n: int) -> list[tuple[int, int, int]]:
    vs: list[tuple[int, int, int]] = []
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                vs.append((a, b, c))
    return vs


def g0_3_1(n: int) -> tuple[Graph, list[tuple[int, int, int]]]:
    vs = triples(n)

    by_first: dict[int, list[int]] = {}
    by_second: dict[int, list[int]] = {}
    for idx, (a, b, _c) in enumerate(vs):
        by_first.setdefault(a, []).append(idx)
        by_second.setdefault(b, []).append(idx)

    edges: list[tuple[int, int]] = []
    for i, (a, b, _c) in enumerate(vs):
        for j in by_first.get(b, []):  # X[1] == Y[0]
            if i != j:
                edges.append((i, j))
        for j in by_second.get(a, []):  # Y[1] == X[0]
            if i != j:
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
    n: int = 11
    subset_sizes: tuple[int, ...] = (12, 14, 16, 18, 20, 22, 25)
    samples_per_k: int = 120
    connected_samples_per_k: int = 160
    maxcut_samples_per_k: int = 30
    seed: int = 0


def main() -> int:
    cfg = Config()
    rng = Random(cfg.seed)  # noqa: S311

    g, vs = g0_3_1(cfg.n)
    adj = adjacency_list(g.n, g.edges)
    comps = connected_components(g.n, adj)

    print("Edge graph test (EHS82 G0(n,3,1) prototype)")
    print(f"  n={cfg.n} |V|=C(n,3)={g.n} |E|={g.m}")
    print("")

    violated = False

    for k in cfg.subset_sizes:
        if k > g.n:
            continue

        worst_eb = -1
        worst_subset: list[int] | None = None

        for j in range(cfg.samples_per_k):
            subset = rng.sample(range(g.n), k)
            if j < cfg.maxcut_samples_per_k:
                sub_edges = induced_subgraph_edges(g.edges, subset)
                e = ebip(k, sub_edges)
                if e > worst_eb:
                    worst_eb = e
                    worst_subset = subset

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
