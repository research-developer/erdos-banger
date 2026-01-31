from __future__ import annotations

from ebip_utils import (
    Graph,
    chromatic_number_exact,
    maxcut_gray,
    normalize_edges,
    sqrt_bound,
)


def paley_graph(q: int) -> Graph:
    """
    Paley graph P(q) for prime q ≡ 1 (mod 4).

    Vertex set: Z/qZ.
    Edge between u != v iff (v-u) is a nonzero quadratic residue mod q.
    """

    if q <= 1 or q % 4 != 1:
        raise ValueError("Paley graph requires q ≡ 1 (mod 4), q > 1")

    residues = {pow(x, 2, q) for x in range(1, q)}
    residues.discard(0)

    edges: list[tuple[int, int]] = []
    for u in range(q):
        for v in range(u + 1, q):
            if (v - u) % q in residues:
                edges.append((u, v))

    return Graph(q, normalize_edges(q, edges))


def main() -> int:
    violated = False
    print("Paley graphs P(q): dense pseudo-random Cayley graphs on Z/qZ")
    for q in (5, 13, 17):
        G = paley_graph(q)
        mc = maxcut_gray(G.n, G.edges)
        deln = G.m - mc
        bound = sqrt_bound(G.n)
        chi = chromatic_number_exact(G.n, G.edges)
        violated |= deln > bound
        print(
            f"  P({q}): |V|={G.n} |E|={G.m} chi={chi} "
            f"MaxCut={mc} ebip={deln} sqrt(|V|)={bound}"
        )

    print("")
    print(f"Violates sqrt bound for some P(q) tested? {violated}")
    return 1 if violated else 0


if __name__ == "__main__":
    raise SystemExit(main())
