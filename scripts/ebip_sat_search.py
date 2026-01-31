"""
SAT/backtracking-style search for finite graphs near the strict √n barrier.

This is **computational-first** infrastructure for Erdős Problem #74:

  Find a graph with χ = ∞ such that for every induced n-vertex subgraph H,
    ebip(H) = |E(H)| - MaxCut(H) ≤ ⌊√n⌋.

We cannot exhaustively quantify over *all* graphs up to n=25, nor over *all*
induced subgraphs for n=25. What we *can* do is:

  1) Run a backtracking search over a constrained edge universe (a "SAT-like"
     boolean search), with pruning driven by *exact* ebip/MaxCut witnesses.
  2) Use counterexample-guided refinement: whenever we find a violating induced
     subgraph, we branch on deleting one of the monochromatic edges from a
     MaxCut witness (deleting such an edge decreases ebip for that witness cut).

The primary initial use-case is:
  - Start from a known 5-chromatic base graph (e.g. Mycielski M5 on 23 vertices),
  - Try to delete edges until the global constraint ebip(G) ≤ ⌊√|V|⌋ holds,
  - Then (optionally) hunt for hereditary violations by searching for violating
    induced subgraphs.

Even negative results here are useful: if *every* attempt to repair many
different 5-chromatic bases collapses to χ ≤ 4 well before the √n constraints
are met, that's evidence for an impossibility direction.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from random import Random
from typing import TYPE_CHECKING

from ebip_utils import (
    chromatic_number_exact,
    ebip_witness,
    induced_subgraph_edges,
    monochromatic_edges_for_assignment,
    normalize_edges,
    sqrt_bound,
)


Edge = tuple[int, int]

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


@dataclass(frozen=True)
class BaseGraph:
    name: str
    n: int
    edges: list[Edge]


def _cycle_graph(n: int) -> BaseGraph:
    if n < 3:
        raise ValueError("cycle graph requires n >= 3")
    edges: list[Edge] = [(i, (i + 1) % n) for i in range(n)]
    return BaseGraph(name=f"C{n}", n=n, edges=normalize_edges(n, edges))


def _mycielskian(n: int, edges: list[Edge]) -> tuple[int, list[Edge]]:
    """
    Mycielski construction M(G).

    Vertex set:
      - originals: 0..n-1
      - shadows:   n..2n-1  (shadow of u is n+u)
      - apex:      2n
    """

    edges_set: set[Edge] = set(edges)

    for u, v in edges:
        u_shadow = n + u
        v_shadow = n + v
        edges_set.add((u_shadow, v) if u_shadow < v else (v, u_shadow))
        edges_set.add((v_shadow, u) if v_shadow < u else (u, v_shadow))

    apex = 2 * n
    for u in range(n):
        u_shadow = n + u
        edges_set.add((apex, u_shadow) if apex < u_shadow else (u_shadow, apex))

    n2 = 2 * n + 1
    return n2, normalize_edges(n2, edges_set)


def base_mycielski(level: int) -> BaseGraph:
    """
    Standard Mycielski sequence starting from C5:
      M3 = C5
      M4 = M(C5)           (Grötzsch graph, χ=4)
      M5 = M(Grötzsch)     (χ=5)
    """

    if level < 3:
        raise ValueError("Mycielski level must be >= 3")

    g = _cycle_graph(5)
    n = g.n
    edges = g.edges
    for _k in range(4, level + 1):
        n, edges = _mycielskian(n, edges)

    return BaseGraph(name=f"Mycielski_M{level}", n=n, edges=edges)


def base_complete(k: int) -> BaseGraph:
    if k <= 0:
        raise ValueError("complete graph requires k > 0")
    edges: list[Edge] = []
    for u in range(k):
        for v in range(u + 1, k):
            edges.append((u, v))
    return BaseGraph(name=f"K{k}", n=k, edges=edges)


def _hajos_join(*, rng: Random, g: BaseGraph, h: BaseGraph) -> BaseGraph:
    """
    Hajós construction: if χ(g) ≥ k and χ(h) ≥ k, then χ(Hajós(g,h)) ≥ k.

    Implementation (randomized orientation):
      - pick an edge a-b in g and c-d in h,
      - delete them,
      - identify a with c,
      - add the edge b-d.

    We build the disjoint union by offsetting h's vertices by g.n, then do a
    single-vertex identification and renumber to 0..(n-1).
    """

    if not g.edges or not h.edges:
        raise ValueError("Hajós join requires graphs with at least one edge")

    # Pick oriented edges.
    u1, v1 = rng.choice(g.edges)
    if rng.random() < 0.5:
        a, b = u1, v1
    else:
        a, b = v1, u1

    u2, v2 = rng.choice(h.edges)
    if rng.random() < 0.5:
        c, d = u2, v2
    else:
        c, d = v2, u2

    n1 = g.n
    n2 = h.n
    c_off = n1 + c
    d_off = n1 + d

    # Edge sets in the disjoint union.
    e1 = (a, b) if a < b else (b, a)
    e2 = (c_off, d_off) if c_off < d_off else (d_off, c_off)

    edges_union: set[Edge] = set(g.edges)
    edges_union.discard(e1)

    for x, y in h.edges:
        x_off = n1 + x
        y_off = n1 + y
        e = (x_off, y_off) if x_off < y_off else (y_off, x_off)
        if e != e2:
            edges_union.add(e)

    # Add the bridge edge b-d (with d mapped later).
    bridge_pre = (b, d_off) if b < d_off else (d_off, b)
    if bridge_pre[0] != bridge_pre[1]:
        edges_union.add(bridge_pre)

    # Identify c_off with a, and renumber by "deleting" c_off (shift down > c_off).
    n_new = n1 + n2 - 1

    def map_vertex(v: int) -> int:
        if v == c_off:
            return a
        if v > c_off:
            return v - 1
        return v

    mapped: set[Edge] = set()
    for x, y in edges_union:
        mx = map_vertex(x)
        my = map_vertex(y)
        if mx == my:
            continue
        e = (mx, my) if mx < my else (my, mx)
        mapped.add(e)

    return BaseGraph(
        name=f"Hajos({g.name},{h.name})",
        n=n_new,
        edges=normalize_edges(n_new, mapped),
    )


def base_hajos_chain(*, rng: Random, target_n: int) -> BaseGraph:
    """
    Build a randomized 5-chromatic-ish graph via repeated Hajós joins with K5.

    Sizes reachable from starting at K5 and joining with K5:
      n = 5 + 4t  (so up to 25: 5, 9, 13, 17, 21, 25)
    """

    if target_n < 5:
        raise ValueError("target_n must be >= 5")
    if (target_n - 5) % 4 != 0:
        raise ValueError("target_n must be 5 (mod 4) for this simple chain builder")

    g = base_complete(5)
    while g.n < target_n:
        g = _hajos_join(rng=rng, g=g, h=base_complete(5))
    return g


@dataclass(frozen=True)
class Violation:
    subset: tuple[int, ...]  # vertex ids in the ambient graph
    ebip: int
    bound: int
    assignment_mask: int  # MaxCut witness assignment for the induced subgraph
    monochromatic_edges: tuple[Edge, ...]  # in ambient vertex ids

    @property
    def k(self) -> int:
        return len(self.subset)


def _induced_edges_ambient(
    ambient_edges: Sequence[Edge], subset: Sequence[int]
) -> list[Edge]:
    """
    Return induced edges but expressed in ambient vertex ids (u,v) with u<v.
    """

    sset = set(subset)
    sub: list[Edge] = []
    for u, v in ambient_edges:
        if u in sset and v in sset:
            sub.append((u, v))
    return sub


def _compute_violation_on_subset(
    *,
    ambient_n: int,
    ambient_edges: list[Edge],
    subset: Sequence[int],
) -> Violation | None:
    k = len(subset)
    if k <= 1:
        return None
    if any(v < 0 or v >= ambient_n for v in subset):
        raise ValueError("subset vertex out of range")

    sub_verts = list(subset)
    sub_edges = induced_subgraph_edges(ambient_edges, sub_verts)
    eb, assignment = ebip_witness(k, sub_edges)
    bnd = sqrt_bound(k)
    if eb <= bnd:
        return None

    mono_sub = monochromatic_edges_for_assignment(sub_edges, assignment)
    # Convert induced-edge indices back to ambient vertex ids.
    ambient_mono: list[Edge] = []
    for i, j in mono_sub:
        u = sub_verts[i]
        v = sub_verts[j]
        ambient_mono.append((u, v) if u < v else (v, u))

    return Violation(
        subset=tuple(sorted(sub_verts)),
        ebip=eb,
        bound=bnd,
        assignment_mask=assignment,
        monochromatic_edges=tuple(sorted(set(ambient_mono))),
    )


def _greedy_minimize_violation_subset(
    *,
    ambient_n: int,
    ambient_edges: list[Edge],
    viol: Violation,
) -> Violation:
    """
    Greedily shrink a violating subset by dropping vertices while it still violates.

    This is not guaranteed to find a minimum-size witness, but it often helps.
    """

    cur = list(viol.subset)
    improved = True
    while improved and len(cur) >= 2:
        improved = False
        for v in list(cur):
            trial = [x for x in cur if x != v]
            trial_viol = _compute_violation_on_subset(
                ambient_n=ambient_n, ambient_edges=ambient_edges, subset=trial
            )
            if trial_viol is not None:
                cur = list(trial_viol.subset)
                viol = trial_viol
                improved = True
                break
    return viol


@dataclass(frozen=True)
class SearchConfig:
    min_chi: int = 5
    # We branch by deleting monochromatic edges of a witness. To keep the tree sane,
    # cap the number of branches per violation.
    branch_limit: int = 10
    max_deletions: int = 40
    time_limit_s: float = 30.0
    # Random subset search parameters for hereditary checking.
    hereditary_samples_per_k: int = 80
    hereditary_subset_sizes: tuple[int, ...] = (25, 24, 23, 22, 20, 18, 16, 14, 12)
    seed: int = 0


@dataclass
class SearchStats:
    nodes: int = 0
    pruned_chi: int = 0
    pruned_depth: int = 0
    pruned_time: int = 0


def _degrees(n: int, edges: Iterable[Edge]) -> list[int]:
    deg = [0] * n
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    return deg


def _maxcut_best_masks_reservoir(
    *,
    rng: Random,
    n: int,
    edges: list[Edge],
    sample_limit: int,
) -> tuple[int, list[int]]:
    """
    Enumerate MaxCut exactly (Gray code) and keep a small reservoir sample of
    *optimal* assignments.

    Returns `(best_cut, best_masks)` where each `best_mask` is a bitmask
    encoding one side of the cut (last vertex fixed to 0).
    """

    if n <= 1:
        return 0, [0]

    if sample_limit <= 0:
        sample_limit = 1

    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    deg = [a.bit_count() for a in adj]

    best = 0
    best_masks: list[int] = [0]
    best_seen = 1

    cut = 0
    prev_g = 0
    limit = 1 << (n - 1)

    for t in range(limit):
        g = t ^ (t >> 1)
        if t:
            flip = g ^ prev_g
            i = flip.bit_length() - 1
            in_s = (prev_g >> i) & 1
            neighbors_in_s = (adj[i] & prev_g).bit_count()
            delta = deg[i] - 2 * neighbors_in_s
            cut += delta if in_s == 0 else -delta

        if cut > best:
            best = cut
            best_masks = [g]
            best_seen = 1
        elif cut == best:
            best_seen += 1
            if len(best_masks) < sample_limit:
                best_masks.append(g)
            else:
                # Reservoir sampling among all optimal assignments.
                j = rng.randrange(best_seen)
                if j < sample_limit:
                    best_masks[j] = g

        prev_g = g

    return best, best_masks


def _pick_branch_edges(
    *,
    n: int,
    current_edges_set: set[Edge],
    viol: Violation,
    branch_limit: int,
) -> list[Edge]:
    """
    Pick a (small) set of edges to branch on, preferring edges whose removal
    heuristically preserves chromatic number (low endpoint degree sum).
    """

    deg = _degrees(n, current_edges_set)
    candidates: list[Edge] = [
        e for e in viol.monochromatic_edges if e in current_edges_set
    ]
    candidates.sort(key=lambda e: (deg[e[0]] + deg[e[1]], e[0], e[1]))
    if branch_limit <= 0:
        return candidates
    return candidates[:branch_limit]


def _find_hereditary_violation(
    *,
    rng: Random,
    ambient_n: int,
    ambient_edges: list[Edge],
    cfg: SearchConfig,
    last_violation_subset: Sequence[int] | None,
) -> Violation | None:
    """
    Try to find an induced-subgraph strict √k violation.

    This is a heuristic search (Monte Carlo + targeted re-check of the last witness).
    """

    if last_violation_subset is not None and len(last_violation_subset) >= 5:
        viol = _compute_violation_on_subset(
            ambient_n=ambient_n,
            ambient_edges=ambient_edges,
            subset=last_violation_subset,
        )
        if viol is not None:
            return _greedy_minimize_violation_subset(
                ambient_n=ambient_n, ambient_edges=ambient_edges, viol=viol
            )

    # Small deterministic check: k=5 is cheap and often catches K5-like obstructions.
    # (We intentionally do not exhaust over larger k at each node.)
    if ambient_n >= 5:
        for _ in range(min(200, cfg.hereditary_samples_per_k)):
            subset = rng.sample(range(ambient_n), 5)
            viol = _compute_violation_on_subset(
                ambient_n=ambient_n, ambient_edges=ambient_edges, subset=subset
            )
            if viol is not None:
                return _greedy_minimize_violation_subset(
                    ambient_n=ambient_n, ambient_edges=ambient_edges, viol=viol
                )

    # Larger k's: sampled search.
    for k in cfg.hereditary_subset_sizes:
        if k > ambient_n or k < 5:
            continue
        for _ in range(cfg.hereditary_samples_per_k):
            subset = rng.sample(range(ambient_n), k)
            viol = _compute_violation_on_subset(
                ambient_n=ambient_n, ambient_edges=ambient_edges, subset=subset
            )
            if viol is not None:
                return _greedy_minimize_violation_subset(
                    ambient_n=ambient_n, ambient_edges=ambient_edges, viol=viol
                )
    return None


def _search_by_edge_deletions(
    *,
    base: BaseGraph,
    cfg: SearchConfig,
    enforce_hereditary: bool,
) -> tuple[list[Edge] | None, SearchStats]:
    """
    SAT/backtracking over a *fixed* base edge set: variables are "keep/delete this edge".
    """

    start = time.monotonic()
    rng = Random(cfg.seed)  # noqa: S311
    stats = SearchStats()

    base_edges = base.edges
    edge_to_index = {e: i for i, e in enumerate(base_edges)}
    full_mask = (1 << len(base_edges)) - 1

    chi_cache: dict[int, int] = {}

    def edges_from_mask(mask: int) -> list[Edge]:
        return [e for i, e in enumerate(base_edges) if (mask >> i) & 1]

    def dfs(  # noqa: PLR0912
        mask: int, depth: int, last_viol: Violation | None
    ) -> list[Edge] | None:
        stats.nodes += 1
        if time.monotonic() - start > cfg.time_limit_s:
            stats.pruned_time += 1
            return None
        if depth > cfg.max_deletions:
            stats.pruned_depth += 1
            return None

        edges = edges_from_mask(mask)

        chi = chi_cache.get(mask)
        if chi is None:
            chi = chromatic_number_exact(base.n, edges)
            chi_cache[mask] = chi
        if chi < cfg.min_chi:
            stats.pruned_chi += 1
            return None

        # Always enforce the whole-graph constraint first (necessary).
        best_cut, best_masks = _maxcut_best_masks_reservoir(
            rng=rng, n=base.n, edges=edges, sample_limit=24
        )
        eb_all = len(edges) - best_cut
        bnd_all = sqrt_bound(base.n)
        if eb_all > bnd_all:
            # Use a union of monochromatic edges from a small sample of optimal cuts,
            # to avoid getting stuck on a single tie-broken witness.
            mono_union: set[Edge] = set()
            for assign in best_masks:
                mono_union.update(monochromatic_edges_for_assignment(edges, assign))
            viol = Violation(
                subset=tuple(range(base.n)),
                ebip=eb_all,
                bound=bnd_all,
                assignment_mask=best_masks[0] if best_masks else 0,
                monochromatic_edges=tuple(sorted(mono_union)),
            )
        elif enforce_hereditary:
            viol = _find_hereditary_violation(
                rng=rng,
                ambient_n=base.n,
                ambient_edges=edges,
                cfg=cfg,
                last_violation_subset=None if last_viol is None else last_viol.subset,
            )
        else:
            viol = None

        if viol is None:
            return edges

        current_edges_set = set(edges)
        branch_edges = _pick_branch_edges(
            n=base.n,
            current_edges_set=current_edges_set,
            viol=viol,
            branch_limit=cfg.branch_limit,
        )

        for e in branch_edges:
            idx = edge_to_index.get(e)
            if idx is None:
                continue
            if ((mask >> idx) & 1) == 0:
                continue
            new_mask = mask & ~(1 << idx)
            result = dfs(new_mask, depth + 1, viol)
            if result is not None:
                return result

        return None

    result_edges = dfs(full_mask, 0, None)
    return result_edges, stats


def search_for_valid_graph(
    max_vertices: int = 25, min_chi: int = 5
) -> list[Edge] | None:
    """
    Entry point requested by the prompt.

    Today this searches within a small set of base 5-chromatic graphs via
    edge-deletion backtracking.

    If this returns a graph, it is a strong candidate (but still needs deeper
    hereditary verification beyond the sampled induced-subgraph checks).
    """

    cfg = SearchConfig(min_chi=min_chi)
    bases: list[BaseGraph] = []

    m5 = base_mycielski(5)
    if m5.n <= max_vertices:
        bases.append(m5)

    # (Optional) pad with isolated vertices to hit max_vertices exactly.
    if bases and bases[0].n < max_vertices:
        base0 = bases[0]
        n_new = max_vertices
        edges_new = base0.edges
        bases.insert(
            0,
            BaseGraph(
                name=f"{base0.name}+{n_new - base0.n}isolates",
                n=n_new,
                edges=edges_new,
            ),
        )

    for base in bases:
        edges, _stats = _search_by_edge_deletions(
            base=base,
            cfg=cfg,
            enforce_hereditary=True,
        )
        if edges is not None:
            return edges

    # Try a few randomized Hajós-chain bases at n=25 (5 mod 4).
    if max_vertices >= 25 and (25 - 5) % 4 == 0:
        rng = Random(0)  # noqa: S311
        for i in range(6):
            haj = base_hajos_chain(rng=rng, target_n=25)
            haj = BaseGraph(name=f"Hajos_chain_{i}", n=haj.n, edges=haj.edges)
            edges, _stats = _search_by_edge_deletions(
                base=haj,
                cfg=cfg,
                enforce_hereditary=True,
            )
            if edges is not None:
                return edges

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backtracking search for graphs near the strict √n ebip barrier."
    )
    parser.add_argument(
        "--base",
        choices=["mycielski5", "mycielski5+isolates", "hajos25"],
        default="mycielski5",
        help="Base graph family to search within (edge-deletion backtracking).",
    )
    parser.add_argument("--min-chi", type=int, default=5, help="Target chromatic.")
    parser.add_argument(
        "--max-deletions",
        type=int,
        default=40,
        help="Maximum number of edge deletions in the search tree.",
    )
    parser.add_argument(
        "--branch-limit",
        type=int,
        default=10,
        help="Limit branching factor per violation (0 means no cap).",
    )
    parser.add_argument(
        "--time-limit-s",
        type=float,
        default=30.0,
        help="Wall-clock time limit (seconds).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RNG seed for induced-subgraph sampling.",
    )
    parser.add_argument(
        "--global-only",
        action="store_true",
        help="Only enforce whole-graph ebip ≤ ⌊√n⌋ (skip hereditary sampling).",
    )
    parser.add_argument(
        "--hajos-samples",
        type=int,
        default=1,
        help="For --base=hajos25: how many random Hajós bases to try.",
    )
    args = parser.parse_args()

    cfg = SearchConfig(
        min_chi=args.min_chi,
        branch_limit=args.branch_limit,
        max_deletions=args.max_deletions,
        time_limit_s=args.time_limit_s,
        seed=args.seed,
    )

    rng = Random(args.seed)  # noqa: S311
    bases: list[BaseGraph] = []

    if args.base.startswith("mycielski5"):
        base = base_mycielski(5)
        if args.base == "mycielski5+isolates":
            if base.n > 25:
                raise SystemExit("Mycielski M5 already exceeds 25 vertices")
            base = BaseGraph(
                name=f"{base.name}+{25 - base.n}isolates", n=25, edges=base.edges
            )
        bases = [base]

    if args.base == "hajos25":
        if args.hajos_samples <= 0:
            raise SystemExit("--hajos-samples must be > 0")
        bases = [
            BaseGraph(
                name=f"Hajos_chain_{i}",
                n=25,
                edges=base_hajos_chain(rng=rng, target_n=25).edges,
            )
            for i in range(args.hajos_samples)
        ]

    for base in bases:
        print(f"Base: {base.name} (n={base.n}, |E|={len(base.edges)})")
        print(
            "Initial:",
            f"chi={chromatic_number_exact(base.n, base.edges)}",
            f"ebip={ebip_witness(base.n, base.edges)[0]}",
            f"floor(sqrt n)={sqrt_bound(base.n)}",
        )
        print("")

        edges, stats = _search_by_edge_deletions(
            base=base,
            cfg=cfg,
            enforce_hereditary=not args.global_only,
        )

        print(
            f"stats: nodes={stats.nodes} pruned(chi={stats.pruned_chi}, "
            f"depth={stats.pruned_depth}, time={stats.pruned_time})"
        )

        if edges is None:
            print("result: no candidate found within limits")
            print("")
            continue

        chi = chromatic_number_exact(base.n, edges)
        eb = ebip_witness(base.n, edges)[0]
        print("result: candidate found")
        print(
            f"  n={base.n} |E|={len(edges)} chi={chi} ebip={eb} "
            f"floor(sqrt n)={sqrt_bound(base.n)}"
        )
        print(f"  edges={edges}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
