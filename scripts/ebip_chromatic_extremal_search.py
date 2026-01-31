"""
Heuristic search for finite graphs with:
  - high chromatic number
  - small ebip = |E| - MaxCut

This is a "meta-approach": instead of guessing a named construction family, we
search the finite design space to see what *extremal* graphs near the √n barrier
look like. If a pattern emerges, it may suggest a genuine construction.

Important: Problem #74 is hereditary (all induced subgraphs). Our search only
checks hereditary constraints by *sampling* induced subgraphs; this is not a
certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from random import Random

from ebip_utils import (
    Graph,
    chromatic_number_exact,
    ebip,
    induced_subgraph_edges,
    normalize_edges,
    sqrt_bound,
)


def random_graph_edges(rng: Random, n: int, p: float) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for u in range(n):
        for v in range(u + 1, n):
            if rng.random() < p:
                edges.append((u, v))
    return edges


def toggle_edge(edges_set: set[tuple[int, int]], u: int, v: int) -> None:
    a, b = (u, v) if u < v else (v, u)
    if a == b:
        return
    if (a, b) in edges_set:
        edges_set.remove((a, b))
    else:
        edges_set.add((a, b))


def hereditary_violation_sample(
    rng: Random,
    g: Graph,
    *,
    subset_sizes: list[int],
    samples_per_k: int,
    maxcut_limit: int = 25,
) -> tuple[int, tuple[int, int] | None]:
    """
    Return (max_excess, (k, ebip_k)) where:
      excess = ebip(G[S]) - floor(sqrt |S|), maximized over sampled subsets.
    """

    best_excess = -(10**9)
    best: tuple[int, int] | None = None

    for k in subset_sizes:
        if k > g.n:
            continue
        for _ in range(samples_per_k):
            subset = rng.sample(range(g.n), k)
            if k > maxcut_limit:
                continue
            sub_edges = induced_subgraph_edges(g.edges, subset)
            e = ebip(k, sub_edges)
            excess = e - sqrt_bound(k)
            if excess > best_excess:
                best_excess = excess
                best = (k, e)
    return best_excess, best


@dataclass(frozen=True)
class Config:
    n: int = 18
    p0: float = 0.18
    steps: int = 6000
    temp0: float = 0.25
    temp_decay: float = 0.9993
    penalty: float = 1.5
    seed: int = 0
    hereditary_subset_sizes: tuple[int, ...] = (8, 10, 12, 14, 16)
    hereditary_samples_per_k: int = 60


def main() -> int:
    cfg = Config()
    rng = Random(cfg.seed)  # noqa: S311

    edges0 = random_graph_edges(rng, cfg.n, cfg.p0)
    edges_set = set(edges0)

    def score_for(edges: list[tuple[int, int]]) -> tuple[float, int, int]:
        e = ebip(cfg.n, edges)
        chi = chromatic_number_exact(cfg.n, edges)
        excess = max(0, e - sqrt_bound(cfg.n))
        score = float(chi) - cfg.penalty * float(excess)
        return score, chi, e

    best_edges = normalize_edges(cfg.n, edges0)
    best_score, best_chi, best_eb = score_for(best_edges)

    cur_edges = best_edges
    cur_score, cur_chi, cur_eb = best_score, best_chi, best_eb
    temp = cfg.temp0

    for step in range(cfg.steps):
        # Propose toggling a random edge.
        u = rng.randrange(cfg.n)
        v = rng.randrange(cfg.n - 1)
        v = v if v < u else v + 1
        toggle_edge(edges_set, u, v)
        proposal = normalize_edges(cfg.n, edges_set)

        s, chi, e = score_for(proposal)

        accept = False
        if s >= cur_score:
            accept = True
        elif rng.random() < exp((s - cur_score) / max(temp, 1e-6)):
            # Simulated annealing.
            accept = True

        if accept:
            cur_edges = proposal
            cur_score, cur_chi, cur_eb = s, chi, e
        else:
            # Revert.
            toggle_edge(edges_set, u, v)

        if cur_score > best_score:
            best_score, best_chi, best_eb = cur_score, cur_chi, cur_eb
            best_edges = cur_edges

        temp *= cfg.temp_decay

        if step % 500 == 0 or step == cfg.steps - 1:
            print(
                f"step={step:4d} temp={temp:.4f} "
                f"cur(chi={cur_chi}, ebip={cur_eb}, score={cur_score:.2f}) "
                f"best(chi={best_chi}, ebip={best_eb}, score={best_score:.2f})"
            )

    print("")
    print("Best found (whole-graph constraints only):")
    print(
        f"  n={cfg.n} |E|={len(best_edges)} "
        f"chi={best_chi} ebip={best_eb} floor(sqrt n)={sqrt_bound(cfg.n)} "
        f"ebip/sqrt(n)={best_eb / sqrt(cfg.n):.2f}"
    )

    g_best = Graph(cfg.n, best_edges)
    excess, witness = hereditary_violation_sample(
        rng,
        g_best,
        subset_sizes=list(cfg.hereditary_subset_sizes),
        samples_per_k=cfg.hereditary_samples_per_k,
    )
    if witness is None:
        print("  hereditary-sample-check: n/a")
    else:
        k, e = witness
        print(
            "  hereditary-sample-check: "
            f"max_excess={excess} at k={k} (ebip={e}, floor(sqrt k)={sqrt_bound(k)})"
        )

    print("")
    print(f"best_edges={best_edges}")

    # Nonzero exit means we found a whole-graph strict violation (not expected).
    return 1 if best_eb > sqrt_bound(cfg.n) else 0


if __name__ == "__main__":
    raise SystemExit(main())
