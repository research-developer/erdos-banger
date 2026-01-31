from __future__ import annotations

from dataclasses import dataclass
from math import isqrt


@dataclass(frozen=True)
class Graph:
    n: int
    # Undirected simple graph edges, stored as (u, v) with u < v.
    edges: list[tuple[int, int]]


def cycle_graph(n: int) -> Graph:
    if n < 3:
        raise ValueError("cycle_graph requires n >= 3")
    edges = [(i, (i + 1) % n) for i in range(n)]
    edges = [(u, v) if u < v else (v, u) for (u, v) in edges]
    return Graph(n, sorted(set(edges)))


def mycielskian(G: Graph) -> Graph:
    """
    Mycielski construction M(G).

    Vertex set:
      - originals: 0..n-1
      - shadows:   n..2n-1  (shadow of u is n+u)
      - apex:      2n

    Edges:
      - original edges E(G)
      - for each uv in E(G), add edges (u', v) and (v', u)
      - connect apex to every shadow vertex
    """

    n = G.n
    edges: set[tuple[int, int]] = set(G.edges)

    for u, v in G.edges:
        u_shadow = n + u
        v_shadow = n + v
        edges.add((u_shadow, v) if u_shadow < v else (v, u_shadow))
        edges.add((v_shadow, u) if v_shadow < u else (u, v_shadow))

    apex = 2 * n
    for u in range(n):
        u_shadow = n + u
        edges.add((apex, u_shadow) if apex < u_shadow else (u_shadow, apex))

    return Graph(2 * n + 1, sorted(edges))


def maxcut_gray(n: int, edges: list[tuple[int, int]]) -> int:
    """
    Exact MaxCut via Gray-code enumeration with O(1) update per step.

    Fix the last vertex color to break symmetry, so the loop runs 2^(n-1) steps.
    Suitable for n up to ~25 on a laptop.
    """

    if n <= 1:
        return 0

    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    deg = [a.bit_count() for a in adj]

    best = 0
    cut = 0
    prev_g = 0
    limit = 1 << (n - 1)  # last vertex fixed to 0

    for t in range(limit):
        g = t ^ (t >> 1)
        if t:
            flip = g ^ prev_g
            i = flip.bit_length() - 1
            in_s = (prev_g >> i) & 1
            neighbors_in_s = (adj[i] & prev_g).bit_count()
            delta = deg[i] - 2 * neighbors_in_s
            cut += delta if in_s == 0 else -delta

        best = max(best, cut)
        prev_g = g

    return best


def main() -> int:
    # Standard Mycielski sequence starting from C5:
    # M3 = C5, M4 = Mycielskian(C5) (Grötzsch graph), etc.
    graphs: dict[int, Graph] = {3: cycle_graph(5)}
    for k in range(4, 6):
        graphs[k] = mycielskian(graphs[k - 1])

    violated = False
    for k in range(3, 6):
        G = graphs[k]
        n = G.n
        m = len(G.edges)
        mc = maxcut_gray(n, G.edges)
        ebip = m - mc
        bound = isqrt(n)
        violated |= ebip > bound
        print(f"M{k}: n={n} m={m} MaxCut={mc} ebip={ebip} sqrt(n)={bound}")

    return 1 if violated else 0


if __name__ == "__main__":
    raise SystemExit(main())
