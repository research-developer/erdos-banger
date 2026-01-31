"""
Ordered edge graphs OE(G,<) (Erdos-Hajnal-Szemeredi 1982, Def. 1.3).

Given a base graph G=(V,E) and a total order < on V:
  - vertices of OE are the edges of G
  - writing X={x0<x1} and Y={y0<y1}, we join X,Y in OE iff
      x1 = y0  OR  y1 = x0.

Special case: OE(K_n, natural order) is the shift graph Sh(n) (already refuted for √n).

This script explores OE applied to *other* base graphs + random vertex orders,
looking for induced subgraphs that violate the strict √n bound.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random

from ebip_utils import Graph, ebip, induced_subgraph_edges, normalize_edges, sqrt_bound


def complete_bipartite(a: int, b: int) -> tuple[int, list[tuple[int, int]]]:
    n = a + b
    edges: list[tuple[int, int]] = []
    for u in range(a):
        for v in range(a, a + b):
            edges.append((u, v))
    return n, edges


def cycle_graph(n: int) -> tuple[int, list[tuple[int, int]]]:
    edges = [(i, (i + 1) % n) for i in range(n)]
    return n, edges


def ordered_edge_graph(
    base_n: int, base_edges: list[tuple[int, int]], order: list[int]
) -> tuple[Graph, list[tuple[int, int]]]:
    """
    Build OE(G,<) and return both:
      - the OE graph (as (n_edges, oe_edges))
      - the list of oriented base edges (x0,x1) corresponding to each OE vertex id
    """

    if sorted(order) != list(range(base_n)):
        raise ValueError("order must be a permutation of range(base_n)")
    rank = {v: i for i, v in enumerate(order)}

    oriented: list[tuple[int, int]] = []
    for u, v in base_edges:
        if u == v:
            continue
        a, b = (u, v) if rank[u] < rank[v] else (v, u)
        oriented.append((a, b))

    # Deduplicate oriented edges.
    oriented = sorted(set(oriented), key=lambda e: (rank[e[0]], rank[e[1]]))

    edges: list[tuple[int, int]] = []
    # Naive O(m^2) construction is fine for small base graphs.
    for i, (x0, x1) in enumerate(oriented):
        for j in range(i + 1, len(oriented)):
            y0, y1 = oriented[j]
            if x1 == y0 or y1 == x0:
                edges.append((i, j))

    g = Graph(len(oriented), normalize_edges(len(oriented), edges))
    return g, oriented


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
class Case:
    name: str
    base_n: int
    base_edges: list[tuple[int, int]]


@dataclass(frozen=True)
class Config:
    # Keep this cheap: exact MaxCut is 2^(k-1), so avoid k=25 unless needed.
    subset_sizes: tuple[int, ...] = (15, 18, 20)
    projections: int = 4  # random orders per base case
    connected_samples_per_k: int = 80
    maxcut_samples_per_k: int = 10
    seed: int = 0


def main() -> int:
    cfg = Config()
    rng = Random(cfg.seed)  # noqa: S311

    cases = [
        Case("K_{6,6} (base bipartite)", *complete_bipartite(6, 6)),
        Case("C_17 (base cycle)", *cycle_graph(17)),
    ]

    any_violation = False

    for case in cases:
        print(f"Ordered edge graph sweep: {case.name}")
        print(f"  base: |V|={case.base_n} |E|={len(case.base_edges)}")

        for _idx in range(cfg.projections):
            order = list(range(case.base_n))
            rng.shuffle(order)

            g, oriented = ordered_edge_graph(case.base_n, case.base_edges, order)
            adj = adjacency_list(g.n, g.edges)
            comps = connected_components(g.n, adj)

            print(
                f"  order_seed={_idx:2d}: OE has |V|={g.n:3d} |E|={g.m:4d} "
                f"(largest component={max(len(c) for c in comps):3d})"
            )

            for k in cfg.subset_sizes:
                if k > g.n:
                    continue
                if not any(len(c) >= k for c in comps):
                    continue

                worst = -1
                worst_subset: list[int] | None = None

                for j in range(cfg.connected_samples_per_k):
                    subset = sample_connected_subset(rng, comps, adj, k)
                    if j >= cfg.maxcut_samples_per_k:
                        continue
                    sub_edges = induced_subgraph_edges(g.edges, subset)
                    e = ebip(k, sub_edges)
                    if e > worst:
                        worst = e
                        worst_subset = subset
                    if e > sqrt_bound(k):
                        break

                ratio = worst / sqrt(k) if worst >= 0 else 0.0
                status = "VIOLATION" if worst > sqrt_bound(k) else "ok"
                print(
                    f"    k={k:2d}: worst_ebip={worst:2d} floor(sqrt k)={sqrt_bound(k)} "
                    f"ratio={ratio:.2f} -> {status}"
                )

                if worst > sqrt_bound(k):
                    any_violation = True
                    subset_sorted = sorted(worst_subset or [])
                    decoded = [
                        {"oe_v": v, "base_edge": oriented[v]} for v in subset_sorted
                    ]
                    print(f"      subset (decoded OE vertices): {decoded}")
                    break

            if any_violation:
                break
        print("")
        if any_violation:
            break

    print(f"Any sampled violation found? {any_violation}")
    return 1 if any_violation else 0


if __name__ == "__main__":
    raise SystemExit(main())
