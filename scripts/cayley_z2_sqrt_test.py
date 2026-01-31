"""
Cayley graphs on (Z/2Z)^d as a "near-bipartite but structured" candidate family.

Vertices: integers 0..2^d-1 representing binary vectors.
Edges: x ~ (x xor g) for g in a generator set S ⊆ (Z/2Z)^d excluding 0.

This family is highly symmetric. The question is whether some generator choice can
force large chromatic number while keeping induced-subgraph ebip under the strict √n bound.

This script is *computational-only*: we sample generator sets and look for small induced
subgraphs that violate ebip(S) <= floor(sqrt |S|), using exact MaxCut for |S|<=25.
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


def cayley_z2(d: int, generators: list[int]) -> Graph:
    n = 1 << d
    edges: list[tuple[int, int]] = []
    for g in generators:
        if g == 0 or g >= n:
            raise ValueError("invalid generator")
        for x in range(n):
            y = x ^ g
            if x < y:
                edges.append((x, y))
    return Graph(n, normalize_edges(n, edges))


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
    d: int = 6
    generator_size: int = 7
    trials: int = 12
    # Keep exact MaxCut cheap: avoid k=25 by default (2^24 steps per call).
    subset_sizes: tuple[int, ...] = (18, 20)
    connected_samples_per_k: int = 90
    maxcut_samples_per_k: int = 12
    seed: int = 0


def main() -> int:
    cfg = Config()
    rng = Random(cfg.seed)  # noqa: S311

    n = 1 << cfg.d
    universe = list(range(1, n))

    print("Cayley (Z/2Z)^d sweep")
    print(
        f"  d={cfg.d} |V|={n} generator_size={cfg.generator_size} trials={cfg.trials}"
    )
    print(f"  subset_sizes={cfg.subset_sizes}, floor(sqrt 25)={sqrt_bound(25)}")
    print("")

    any_violation = False

    for t in range(cfg.trials):
        generators = rng.sample(universe, cfg.generator_size)
        g = cayley_z2(cfg.d, generators)
        adj = adjacency_list(g.n, g.edges)
        comps = connected_components(g.n, adj)

        print(
            f"trial={t:2d}: |E|={g.m:4d}, "
            f"largest_component={max(len(c) for c in comps):3d}, "
            f"generators={sorted(generators)}"
        )

        for k in cfg.subset_sizes:
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
                f"  k={k:2d}: worst_ebip={worst:2d} floor(sqrt k)={sqrt_bound(k)} "
                f"ratio={ratio:.2f} -> {status}"
            )

            if worst > sqrt_bound(k):
                any_violation = True
                subset_sorted = sorted(worst_subset or [])
                sub_edges = induced_subgraph_edges(g.edges, subset_sorted)
                chi = chromatic_number_exact(k, sub_edges)
                print(f"    chi(subset)={chi}, subset={subset_sorted}")
                break

        if any_violation:
            break
        print("")

    print("")
    print(f"Any sampled violation found? {any_violation}")
    return 1 if any_violation else 0


if __name__ == "__main__":
    raise SystemExit(main())
