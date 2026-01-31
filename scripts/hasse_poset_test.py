"""
Experiments for Erdős Problem #74 via the Suk-Tomon Hasse-diagram construction.

This implements (a small-scale variant of) Claim 12 in:
  Istvan Tomon, "Hasse diagrams with large chromatic number"

Vertices are point-line incidences (p, l). Edges are defined via a length-2 path
in the incidence graph with monotonicity constraints in a total order `prec` that
simulates "x-coordinate of p" and "slope of l".

For random induced subsets S we compare:
  - ebip(G[S]) = |E| - MaxCut (exact for |S| <= ~25)
  - defect(S): monochromatic edges under the parity coloring given by induced
    poset heights mod 2 (the "rank-parity defect" heuristic).

The defect count is a *constructive* upper bound on ebip(G[S]) and is meant to
probe whether ebip might scale like O(sqrt |S|) on this family.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from random import Random
from typing import TYPE_CHECKING

from ebip_utils import (
    Graph,
    ebip,
    induced_subgraph_edges,
    normalize_edges,
    sqrt_bound,
)


if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    @property
    def x_key(self) -> int:
        # Injective "x-coordinate" used only to define a total order on points.
        # This is a deterministic tie-breaker consistent with a generic shear.
        return (self.x << 20) + self.y


@dataclass(frozen=True)
class Line:
    slope: int
    intercept: int

    @property
    def slope_key(self) -> int:
        # Injective "slope" key used only to define a total order on lines.
        return (self.slope << 20) + self.intercept


@dataclass(frozen=True)
class Incidence:
    p: int  # point id
    line: int  # line id


def standard_point_line_configuration(t: int) -> tuple[list[Point], list[Line]]:
    """
    A small explicit point/line configuration with about |I| ~ t^4 incidences.

    We follow the "standard example" cited in Tomon's paper (scaled by t):
      Points:  P = {(x,y): 0<=x<t, 0<=y<t^2}
      Lines:   L = {y = a x + b : 0<=a<t, 0<=b<t^2}

    Note: Points do not have distinct geometric x-coordinates and lines have
    repeated slopes; the construction in the paper applies a projective
    transformation to remove these degeneracies. Here we model this by using
    injective order-keys `x_key` and `slope_key` while keeping the same incidence
    relation.
    """

    if t <= 0:
        raise ValueError("t must be positive")

    t2 = t * t
    points = [Point(x, y) for x in range(t) for y in range(t2)]
    lines = [Line(a, b) for a in range(t) for b in range(t2)]
    return points, lines


def incidences(points: list[Point], lines: list[Line]) -> list[Incidence]:
    inc: list[Incidence] = []
    for pid, p in enumerate(points):
        for lid, ln in enumerate(lines):
            if p.y == ln.slope * p.x + ln.intercept:
                inc.append(Incidence(pid, lid))
    return inc


def suk_tomon_graph_standard(
    t: int,
) -> tuple[Graph, list[Incidence], list[Point], list[Line]]:
    """
    Build the undirected Hasse diagram-style graph G_t on incidence vertices.

    Vertices: incidences (p, l) with p in l
    Total order `prec` on vertices: by (x_key(p), slope_key(l))
    Edge rule (Tomon Claim 12): connect (p,l) - (p',l') if
      x_key(p) < x_key(p') and slope_key(l) < slope_key(l') and p' in l.
    """

    points, lines = standard_point_line_configuration(t)
    inc = incidences(points, lines)

    # Sort incidences by the total order key (x_key(point), slope_key(line)).
    def order_key(z: Incidence) -> tuple[int, int]:
        p = points[z.p]
        ln = lines[z.line]
        return (p.x_key, ln.slope_key)

    inc_sorted = sorted(inc, key=order_key)
    vid: dict[tuple[int, int], int] = {
        (z.p, z.line): i for i, z in enumerate(inc_sorted)
    }

    # Precompute incidences grouped by point and line for fast edge generation.
    points_on_line: list[list[int]] = [[] for _ in range(len(lines))]
    lines_at_point: list[list[int]] = [[] for _ in range(len(points))]

    for z in inc_sorted:
        points_on_line[z.line].append(z.p)
        lines_at_point[z.p].append(z.line)

    # Sort each incidence list by the relevant order key.
    for lid in range(len(lines)):
        points_on_line[lid].sort(key=lambda pid: points[pid].x_key)
    for pid in range(len(points)):
        lines_at_point[pid].sort(key=lambda lid: lines[lid].slope_key)

    pos_in_line: dict[tuple[int, int], int] = {}
    for lid, ps in enumerate(points_on_line):
        for j, pid in enumerate(ps):
            pos_in_line[(lid, pid)] = j

    pos_in_point: dict[tuple[int, int], int] = {}
    for pid, ls in enumerate(lines_at_point):
        for j, lid in enumerate(ls):
            pos_in_point[(pid, lid)] = j

    edges: list[tuple[int, int]] = []

    # Enumerate "pivot" incidences (p', l) and hook up points before p' on l
    # to lines after l at p'.
    for p_prime in range(len(points)):
        lines_here = lines_at_point[p_prime]
        for line in lines_here:
            ppos = pos_in_line[(line, p_prime)]
            lpos = pos_in_point[(p_prime, line)]

            pts_before = points_on_line[line][:ppos]
            lines_after = lines_here[lpos + 1 :]

            if not pts_before or not lines_after:
                continue

            for p in pts_before:
                u = vid[(p, line)]
                for line_prime in lines_after:
                    v = vid[(p_prime, line_prime)]
                    edges.append((u, v))

    n = len(inc_sorted)
    return Graph(n, normalize_edges(n, edges)), inc_sorted, points, lines


def reachability_bitsets(n: int, edges: list[tuple[int, int]]) -> list[int]:
    """
    Compute reachability in the DAG obtained by orienting edges from smaller id
    to larger id (ids are already in `prec` order by construction).

    Returns reach[u] as a bitset of vertices v reachable from u with v>u.
    """

    out: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        if u == v:
            continue
        a, b = (u, v) if u < v else (v, u)
        out[a].append(b)

    reach = [0] * n
    for u in range(n - 1, -1, -1):
        r = 0
        for v in out[u]:
            r |= reach[v] | (1 << v)
        reach[u] = r
    return reach


def adjacency_list(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        if u == v:
            continue
        adj[u].append(v)
        adj[v].append(u)
    return adj


def sample_connected_subset(
    rng: Random, comps: list[list[int]], adj: list[list[int]], k: int
) -> list[int]:
    """
    Sample a connected vertex subset of size k by growing from a random seed in a
    component with size >= k.
    """

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
            raise AssertionError("frontier unexpectedly empty in a large component")
        v = frontier.pop(rng.randrange(len(frontier)))
        if v in in_subset:
            continue
        in_subset.add(v)
        subset.append(v)
        for w in adj[v]:
            if w not in in_subset:
                frontier.append(w)

    return subset


def induced_heights(reach: list[int], subset: Iterable[int]) -> dict[int, int]:
    """
    Height h_S(x) in the induced subposet (restricted order) where the poset
    order is the transitive closure of the oriented edges (reachability).
    """

    verts = sorted(set(subset))
    h: dict[int, int] = {}
    for i, v in enumerate(verts):
        best = 0
        for u in verts[:i]:
            if (reach[u] >> v) & 1:
                best = max(best, h[u])
        h[v] = best + 1
    return h


def defect_count(
    edges: list[tuple[int, int]], heights: dict[int, int], subset_set: set[int]
) -> int:
    d = 0
    for u, v in edges:
        if u not in subset_set or v not in subset_set:
            continue
        if (heights[u] ^ heights[v]) & 1:
            continue
        d += 1
    return d


def experiment(  # noqa: PLR0915
    t: int,
    subset_sizes: list[int],
    samples_per_size: int,
    seed: int = 0,
    exact_maxcut_limit: int = 25,
    maxcut_samples_per_size: int = 25,
    connected_samples_per_size: int = 80,
) -> int:
    rng = Random(seed)  # noqa: S311
    G, inc_sorted, points, lines = suk_tomon_graph_standard(t)
    reach = reachability_bitsets(G.n, G.edges)
    adj = adjacency_list(G.n, G.edges)

    # Connected components for connected-subset sampling.
    comps: list[list[int]] = []
    seen = [False] * G.n
    for s in range(G.n):
        if seen[s]:
            continue
        q = [s]
        seen[s] = True
        comp: list[int] = []
        while q:
            u = q.pop()
            comp.append(u)
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    q.append(v)
        comps.append(comp)

    print(f"Suk-Tomon standard example (t={t})")
    print(
        f"  |P|={len(points)} |L|={len(lines)} |I|=|V|={G.n} |E|={G.m} "
        f"(expected |I|≈t^4={t**4})"
    )
    print("")

    violated = False

    def run_samples(
        k: int, sample_fn, n_samples: int
    ) -> tuple[int, int, float, float, tuple[int, int, int, list[int]] | None]:
        max_eb = -1
        max_d = -1
        max_eb_ratio = 0.0
        max_d_ratio = 0.0
        worst: tuple[int, int, int, list[int]] | None = None

        for j in range(n_samples):
            subset = sample_fn()
            subset_set = set(subset)

            heights = induced_heights(reach, subset)
            d = defect_count(G.edges, heights, subset_set)

            if j < maxcut_samples_per_size and k <= exact_maxcut_limit:
                sub_edges = induced_subgraph_edges(G.edges, subset)
                e = ebip(k, sub_edges)
            else:
                e = -1

            if e >= 0 and e > d:
                raise AssertionError(f"bug: ebip={e} > defects={d} for k={k}")

            max_d = max(max_d, d)
            max_d_ratio = max(max_d_ratio, d / sqrt(k))

            if e >= 0:
                max_eb = max(max_eb, e)
                max_eb_ratio = max(max_eb_ratio, e / sqrt(k))
                if e > sqrt_bound(k) and (worst is None or e > worst[0]):
                    worst = (e, d, k, subset)

        return max_eb, max_d, max_eb_ratio, max_d_ratio, worst

    for k in subset_sizes:
        if k > G.n:
            continue

        eb_u, d_u, eb_u_r, d_u_r, worst_u = run_samples(
            k=k,
            sample_fn=lambda k=k: rng.sample(range(G.n), k),
            n_samples=samples_per_size,
        )
        if any(len(c) >= k for c in comps):
            eb_c, d_c, eb_c_r, d_c_r, worst_c = run_samples(
                k=k,
                sample_fn=lambda k=k: sample_connected_subset(rng, comps, adj, k),
                n_samples=connected_samples_per_size,
            )
        else:
            eb_c, d_c, eb_c_r, d_c_r, worst_c = (-1, -1, 0.0, 0.0, None)

        bound = sqrt_bound(k)
        connected_label = (
            f"connected(max_def={d_c:3d}, /{sqrt(k):.2f}≈{d_c_r:.2f}; "
            f"max_ebip={eb_c:3d}, /{sqrt(k):.2f}≈{eb_c_r:.2f})"
            if d_c >= 0
            else "connected(n/a)"
        )
        print(
            f"  k={k:2d}: "
            f"uniform(max_def={d_u:3d}, /{sqrt(k):.2f}≈{d_u_r:.2f}; "
            f"max_ebip={eb_u:3d}, /{sqrt(k):.2f}≈{eb_u_r:.2f}) | "
            f"{connected_label} "
            f"(floor(sqrt k)={bound})"
        )

        for worst in [worst_u, worst_c]:
            if worst is None:
                continue
            e, d, kk, subset = worst
            violated = True
            print(
                f"        sample violation: ebip={e} > floor(sqrt {kk})={sqrt_bound(kk)} "
                f"(defects={d})"
            )
            decoded = []
            for v in subset:
                inc = inc_sorted[v]
                p = points[inc.p]
                ln = lines[inc.line]
                decoded.append(((p.x, p.y), (ln.slope, ln.intercept)))
            print(f"        subset vertex ids: {sorted(subset)}")
            print(f"        subset incidences: {decoded}")

    print("")
    print(f"Any sampled violation of the strict √n bound? {violated}")
    print(
        "Note: this is Monte Carlo; 'no violation' does not certify anything. "
        "A single violation is a real counterexample subset."
    )

    # Return nonzero if we found a genuine violating induced subset (for the strict constant-1 bound).
    return 1 if violated else 0


def main() -> int:
    # Keep MaxCut work bounded: we only compute exact MaxCut for a small number of
    # samples at each k, since it scales like 2^(k-1).
    subset_sizes = [10, 12, 14, 16, 18, 20, 22, 25]
    samples_per_size = 200
    connected_samples_per_size = 120
    maxcut_samples_per_size = 10

    violated_any = False
    for t in [2, 3, 4]:
        code = experiment(
            t=t,
            subset_sizes=subset_sizes,
            samples_per_size=samples_per_size,
            seed=17 + t,
            exact_maxcut_limit=25,
            maxcut_samples_per_size=maxcut_samples_per_size,
            connected_samples_per_size=connected_samples_per_size,
        )
        violated_any |= code != 0
        print("\n" + ("-" * 72) + "\n")

    return 1 if violated_any else 0


if __name__ == "__main__":
    raise SystemExit(main())
