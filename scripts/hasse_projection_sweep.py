"""
Sweep random projective transforms for the Suk-Tomon "standard configuration".

Goal: check whether the strict `ebip(H) <= floor(sqrt |V(H)|)` bound already fails
robustly on small induced subgraphs (e.g. |S|=25) across many projections.

This is computational evidence only (not exhaustive).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random

from ebip_utils import ebip, induced_subgraph_edges, sqrt_bound
from hasse_poset_test import (
    adjacency_list,
    sample_connected_subset,
    suk_tomon_graph_standard,
)


@dataclass(frozen=True)
class SweepConfig:
    t: int = 4
    k: int = 25
    projections: int = 8
    samples_per_projection: int = 6
    seed: int = 0


def main() -> int:
    cfg = SweepConfig()
    rng = Random(cfg.seed)  # noqa: S311

    print(
        "Hasse projection sweep\n"
        f"  t={cfg.t} k={cfg.k} projections={cfg.projections} "
        f"samples_per_projection={cfg.samples_per_projection}"
    )
    print(f"  sqrt(k)={sqrt(cfg.k):.3f}, floor(sqrt k)={sqrt_bound(cfg.k)}")
    print("")

    any_violation = False

    for _idx in range(cfg.projections):
        proj_seed = rng.randrange(1_000_000_000)
        (
            g,
            _inc_sorted,
            _points,
            _lines,
            _point_x,
            _line_slope,
            proj_m,
        ) = suk_tomon_graph_standard(
            cfg.t, use_projective_transform=True, projection_seed=proj_seed
        )
        adj = adjacency_list(g.n, g.edges)

        # Components (for connected-subset sampling).
        comps: list[list[int]] = []
        seen = [False] * g.n
        for s in range(g.n):
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

        worst = -1
        worst_subset: list[int] | None = None
        violated = False

        for _j in range(cfg.samples_per_projection):
            subset = sample_connected_subset(rng, comps, adj, cfg.k)
            sub_edges = induced_subgraph_edges(g.edges, subset)
            e = ebip(cfg.k, sub_edges)
            if e > worst:
                worst = e
                worst_subset = subset
            if e > sqrt_bound(cfg.k):
                violated = True
                break

        ratio = worst / sqrt(cfg.k)
        print(
            f"  proj_seed={proj_seed:10d}: |V|={g.n:4d} |E|={g.m:5d} "
            f"worst_ebip={worst:2d} ratio={ratio:.2f} violated? {violated}"
        )
        if violated:
            any_violation = True
            print(f"    matrix={proj_m}")
            print(f"    subset={sorted(worst_subset or [])}")

    print("")
    print(f"Any violation found across projections? {any_violation}")
    return 1 if any_violation else 0


if __name__ == "__main__":
    raise SystemExit(main())
