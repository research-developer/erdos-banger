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
from fractions import Fraction
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


Matrix3 = tuple[
    tuple[Fraction, Fraction, Fraction],
    tuple[Fraction, Fraction, Fraction],
    tuple[Fraction, Fraction, Fraction],
]


def _det3(m: Matrix3) -> Fraction:
    (a, b, c), (d, e, f), (g, h, i) = m
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _inv3(m: Matrix3) -> Matrix3:
    (a, b, c), (d, e, f), (g, h, i) = m
    det = _det3(m)
    if det == 0:
        raise ValueError("singular matrix")

    c11 = e * i - f * h
    c12 = -(d * i - f * g)
    c13 = d * h - e * g

    c21 = -(b * i - c * h)
    c22 = a * i - c * g
    c23 = -(a * h - b * g)

    c31 = b * f - c * e
    c32 = -(a * f - c * d)
    c33 = a * e - b * d

    inv_det = Fraction(1, 1) / det
    return (
        (c11 * inv_det, c21 * inv_det, c31 * inv_det),
        (c12 * inv_det, c22 * inv_det, c32 * inv_det),
        (c13 * inv_det, c23 * inv_det, c33 * inv_det),
    )


def _mat_mul_vec(
    m: Matrix3, v: tuple[Fraction, Fraction, Fraction]
) -> tuple[Fraction, Fraction, Fraction]:
    (a, b, c), (d, e, f), (g, h, i) = m
    x, y, z = v
    return (
        a * x + b * y + c * z,
        d * x + e * y + f * z,
        g * x + h * y + i * z,
    )


def _row_mul_mat(
    row: tuple[Fraction, Fraction, Fraction], m: Matrix3
) -> tuple[Fraction, Fraction, Fraction]:
    (a, b, c), (d, e, f), (g, h, i) = m
    r0, r1, r2 = row
    return (
        r0 * a + r1 * d + r2 * g,
        r0 * b + r1 * e + r2 * h,
        r0 * c + r1 * f + r2 * i,
    )


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
    repeated slopes; the paper applies a projective transformation ("projection")
    to remove these degeneracies without changing incidences.

    In this repo we support two experimental modes:
    - `mode=order-keys`: deterministic injective order-keys (`x_key`, `slope_key`)
    - `mode=projective-transform`: sample a projective transform and use the
      induced real x-coordinates / slopes (see `find_projection_with_distinct_x_and_slopes`)
    """

    if t <= 0:
        raise ValueError("t must be positive")

    t2 = t * t
    points = [Point(x, y) for x in range(t) for y in range(t2)]
    lines = [Line(a, b) for a in range(t) for b in range(t2)]
    return points, lines


def find_projection_with_distinct_x_and_slopes(
    points: list[Point],
    lines: list[Line],
    rng: Random,
    *,
    max_attempts: int = 2000,
    entry_bound: int = 5,
) -> tuple[Matrix3, list[Fraction], list[Fraction]]:
    """
    Find a projective transformation of the plane that makes:
      - all point x-coordinates distinct, and
      - all line slopes distinct,
    while preserving the incidence structure.

    We follow the paper's statement that this can be done "by applying a projection".
    Computationally, we just sample random invertible 3x3 matrices and reject those
    that cause degeneracies (points at infinity / vertical lines / collisions).
    """

    pts = [
        (Fraction(p.x), Fraction(p.y), Fraction(1, 1))  # homogeneous coordinate
        for p in points
    ]
    # Line y = a x + b corresponds to: a x - y + b = 0, i.e. (A,B,C) = (a, -1, b).
    lns = [
        (Fraction(ln.slope), Fraction(-1, 1), Fraction(ln.intercept)) for ln in lines
    ]

    for _ in range(max_attempts):
        m_int = tuple(
            tuple(rng.randint(-entry_bound, entry_bound) for _ in range(3))
            for _ in range(3)
        )
        m = tuple(
            tuple(Fraction(x, 1) for x in row)  # type: ignore[misc]
            for row in m_int
        )
        if _det3(m) == 0:
            continue
        inv = _inv3(m)

        # Transform points.
        x_coords: list[Fraction] = []
        ok = True
        for pvec in pts:
            x, _y, z = _mat_mul_vec(m, pvec)
            if z == 0:
                ok = False
                break
            x_coords.append(x / z)
        if not ok or len(set(x_coords)) != len(points):
            continue

        # Transform lines.
        slopes: list[Fraction] = []
        for lvec in lns:
            a, b, _c = _row_mul_mat(lvec, inv)
            if b == 0:
                ok = False
                break
            slopes.append(-a / b)
        if not ok or len(set(slopes)) != len(lines):
            continue

        # Sanity: incidence is preserved by construction (l * inv) * (m * p) = l * p.
        return m, x_coords, slopes

    raise RuntimeError("failed to find a suitable projective transform")


def incidences(points: list[Point], lines: list[Line]) -> list[Incidence]:
    inc: list[Incidence] = []
    for pid, p in enumerate(points):
        for lid, ln in enumerate(lines):
            if p.y == ln.slope * p.x + ln.intercept:
                inc.append(Incidence(pid, lid))
    return inc


def suk_tomon_graph_standard(  # noqa: PLR0912
    t: int,
    *,
    use_projective_transform: bool = False,
    projection_seed: int = 0,
) -> tuple[
    Graph,
    list[Incidence],
    list[Point],
    list[Line],
    list[Fraction],
    list[Fraction],
    Matrix3 | None,
]:
    """
    Build the undirected Hasse diagram-style graph G_t on incidence vertices.

    Vertices: incidences (p, l) with p in l
    Total order `prec` on vertices: by (x_key(p), slope_key(l))
    Edge rule (Tomon Claim 12): connect (p,l) - (p',l') if
      x_key(p) < x_key(p') and slope_key(l) < slope_key(l') and p' in l.
    """

    points, lines = standard_point_line_configuration(t)
    inc = incidences(points, lines)

    if use_projective_transform:
        proj_rng = Random(projection_seed)  # noqa: S311
        proj_m, point_x, line_slope = find_projection_with_distinct_x_and_slopes(
            points,
            lines,
            proj_rng,
        )
    else:
        proj_m = None
        point_x = [Fraction(p.x_key, 1) for p in points]
        line_slope = [Fraction(ln.slope_key, 1) for ln in lines]

    # Sort incidences by the total order key (x_key(point), slope_key(line)).
    def order_key(z: Incidence) -> tuple[Fraction, Fraction]:
        return (point_x[z.p], line_slope[z.line])

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
        points_on_line[lid].sort(key=lambda pid: point_x[pid])
    for pid in range(len(points)):
        lines_at_point[pid].sort(key=lambda lid: line_slope[lid])

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
    return (
        Graph(n, normalize_edges(n, edges)),
        inc_sorted,
        points,
        lines,
        point_x,
        line_slope,
        proj_m,
    )


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


def experiment(  # noqa: PLR0912, PLR0915
    t: int,
    subset_sizes: list[int],
    samples_per_size: int,
    seed: int = 0,
    exact_maxcut_limit: int = 25,
    maxcut_samples_per_size: int = 25,
    connected_samples_per_size: int = 80,
    use_projective_transform: bool = False,
    projection_seed: int | None = None,
) -> int:
    rng = Random(seed)  # noqa: S311
    proj_seed = seed + 1_000_003 if projection_seed is None else projection_seed
    (
        G,
        inc_sorted,
        points,
        lines,
        point_x,
        line_slope,
        proj_m,
    ) = suk_tomon_graph_standard(
        t,
        use_projective_transform=use_projective_transform,
        projection_seed=proj_seed,
    )
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

    mode = "projective-transform" if use_projective_transform else "order-keys"
    print(f"Suk-Tomon standard example (t={t}, mode={mode})")
    print(
        f"  |P|={len(points)} |L|={len(lines)} |I|=|V|={G.n} |E|={G.m} "
        f"(expected |I|≈t^4={t**4})"
    )
    if use_projective_transform and proj_m is not None:
        print(f"  projection_seed={proj_seed}, matrix={proj_m}")
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
                decoded.append(
                    {
                        "v": v,
                        "p": inc.p,
                        "line": inc.line,
                        "p_xy": (p.x, p.y),
                        "line_ab": (ln.slope, ln.intercept),
                        "x_order": str(point_x[inc.p]),
                        "slope_order": str(line_slope[inc.line]),
                    }
                )
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
