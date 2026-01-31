from __future__ import annotations

from itertools import combinations

from ebip_utils import (
    Graph,
    chromatic_number_exact,
    maxcut_gray,
    normalize_edges,
    sqrt_bound,
)


def kneser_graph(n: int, k: int) -> Graph:
    """
    Kneser graph K(n, k):
      - vertices are k-subsets of {0, ..., n-1}
      - edges connect disjoint subsets
    """

    if not (0 <= k <= n):
        raise ValueError("need 0 <= k <= n")

    subsets = list(combinations(range(n), k))
    masks: list[int] = []
    for s in subsets:
        m = 0
        for i in s:
            m |= 1 << i
        masks.append(m)

    edges: list[tuple[int, int]] = []
    for i in range(len(masks)):
        for j in range(i + 1, len(masks)):
            if masks[i] & masks[j] == 0:
                edges.append((i, j))

    return Graph(len(masks), normalize_edges(len(masks), edges))


def main() -> int:
    violated = False
    print("Kneser graphs K(n,2) (Lovász: chi = n-2 for n>=4)")

    for n in (5, 6, 7):
        G = kneser_graph(n, 2)
        mc = maxcut_gray(G.n, G.edges)
        deln = G.m - mc
        bound = sqrt_bound(G.n)
        chi = chromatic_number_exact(G.n, G.edges)
        violated |= deln > bound
        print(
            f"  K({n},2): |V|={G.n} |E|={G.m} chi={chi} "
            f"MaxCut={mc} ebip={deln} sqrt(|V|)={bound}"
        )

    print("")
    print(f"Violates sqrt bound for some K(n,2) tested? {violated}")
    return 1 if violated else 0


if __name__ == "__main__":
    raise SystemExit(main())
