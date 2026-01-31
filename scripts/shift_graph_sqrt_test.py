from __future__ import annotations

from dataclasses import dataclass

from ebip_utils import (
    Graph,
    chromatic_number_exact,
    maxcut_gray,
    normalize_edges,
    sqrt_bound,
)


@dataclass(frozen=True)
class Pair:
    i: int
    j: int


def shift_graph(n: int) -> Graph:
    """
    The (undirected) shift graph Sh(n):

    - Vertices are ordered pairs (i, j) with 0 <= i < j < n.
    - Edge between (i, j) and (j, k) for i < j < k.

    This is the standard triangle-free graph with chi(Sh(n)) ~ log2(n).
    """

    if n < 2:
        return Graph(0, [])

    verts: list[Pair] = [Pair(i, j) for i in range(n) for j in range(i + 1, n)]
    vid = {(p.i, p.j): t for t, p in enumerate(verts)}

    edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                u = vid[(i, j)]
                v = vid[(j, k)]
                edges.append((u, v))

    return Graph(len(verts), normalize_edges(len(verts), edges))


def main() -> int:
    violated = False

    print("Shift graphs Sh(n): vertices are pairs (i,j), edges are shifts (i,j)-(j,k)")
    for n in range(3, 8):
        G = shift_graph(n)
        mc = maxcut_gray(G.n, G.edges)
        deln = G.m - mc
        bound = sqrt_bound(G.n)
        chi = chromatic_number_exact(G.n, G.edges)
        violated |= deln > bound
        print(
            f"  Sh({n}): |V|={G.n} |E|={G.m} chi={chi} "
            f"MaxCut={mc} ebip={deln} sqrt(|V|)={bound}"
        )

    print("")
    print(f"Violates sqrt bound for some Sh(n) tested? {violated}")

    return 1 if violated else 0


if __name__ == "__main__":
    raise SystemExit(main())
