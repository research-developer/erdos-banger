from __future__ import annotations

from dataclasses import dataclass
from math import isqrt


@dataclass(frozen=True)
class Graph:
    n: int
    # Undirected simple graph edges, stored as (u, v) with u < v.
    edges: list[tuple[int, int]]


def next_burling(G: Graph, stable_sets: list[set[int]]) -> tuple[Graph, list[set[int]]]:
    """
    Burling sequence step `next_B` from arXiv:2104.07001 (Burling revisited I), Def. 4.1.

    Input:
      - `G`: graph with vertices {0, ..., n-1}
      - `stable_sets`: a family of stable sets of G, represented as sets of vertex ids

    Output:
      - `G'`: next Burling graph
      - `stable_sets'`: next stable-set family
    """

    n = G.n

    def copy_edges(offset: int) -> list[tuple[int, int]]:
        return [(u + offset, v + offset) for (u, v) in G.edges]

    # Step (i): Take a copy of G.
    edges: list[tuple[int, int]] = []
    edges += copy_edges(0)
    next_vid = n

    # Keep stable sets for the first copy.
    stable_sets_first = [set(S) for S in stable_sets]

    # Step (ii): For each stable set S, take a new copy of G, denoted G_S.
    copy_offsets: list[int] = []
    for _ in stable_sets:
        off = next_vid
        copy_offsets.append(off)
        edges += copy_edges(off)
        next_vid += n

    # Step (iii): For each S and each Q in the copied family, add v_{S,Q} adjacent to all vertices in Q.
    stable_sets_prime: list[set[int]] = []
    for S_idx, S in enumerate(stable_sets_first):
        off = copy_offsets[S_idx]
        for Q in stable_sets:
            Qc = {q + off for q in Q}
            v_new = next_vid
            next_vid += 1
            for q in Qc:
                u, v = (q, v_new) if q < v_new else (v_new, q)
                edges.append((u, v))
            # Step (v): stable sets of the form S union Q and S union {v_{S,Q}}.
            stable_sets_prime.append(set(S) | set(Qc))
            stable_sets_prime.append(set(S) | {v_new})

    edges = [(u, v) if u < v else (v, u) for (u, v) in edges]
    edges = sorted(set(edges))

    return Graph(next_vid, edges), stable_sets_prime


def induced_subgraph_edges(
    edges: list[tuple[int, int]], verts: list[int]
) -> list[tuple[int, int]]:
    idx = {v: i for i, v in enumerate(verts)}
    vset = set(verts)
    sub: list[tuple[int, int]] = []
    for u, v in edges:
        if u in vset and v in vset:
            sub.append((idx[u], idx[v]))
    return sub


def maxcut_bruteforce(n: int, edges: list[tuple[int, int]]) -> int:
    """
    Exact MaxCut by brute force (fix last vertex color to break symmetry).
    Suitable for n <= ~22.
    """

    if n <= 1:
        return 0

    us = [u for u, _ in edges]
    vs = [v for _, v in edges]
    m = len(edges)

    best = 0
    for a in range(1 << (n - 1)):
        cut = 0
        for i in range(m):
            u = us[i]
            v = vs[i]
            cu = (a >> u) & 1 if u < n - 1 else 0
            cv = (a >> v) & 1 if v < n - 1 else 0
            cut += cu ^ cv
        best = max(best, cut)
    return best


def main() -> int:
    # Build G1.
    G1 = Graph(1, [])
    S1 = [{0}]

    # Build G2, G3, G4.
    G2, S2 = next_burling(G1, S1)
    G3, S3 = next_burling(G2, S2)
    G4, S4 = next_burling(G3, S3)

    print(f"G1: n={G1.n} m={len(G1.edges)} |S|={len(S1)}")
    print(f"G2: n={G2.n} m={len(G2.edges)} |S|={len(S2)}")
    print(f"G3: n={G3.n} m={len(G3.edges)} |S|={len(S3)}")
    print(f"G4: n={G4.n} m={len(G4.edges)} |S|={len(S4)}")

    # In this construction, G4 is the disjoint union of:
    # - a base copy of G3 on vertices [0, ..., 12]
    # - for each S in S3 (|S3|=8), a component consisting of a copy of G3 (13 vertices)
    #   plus 8 new vertices adjacent to stable sets inside that copy (total 21 vertices).
    n3 = G3.n
    s3 = len(S3)
    if n3 != 13 or s3 != 8:
        raise ValueError(f"Expected n3=13, s3=8, got n3={n3}, s3={s3}")

    # Pick the first nontrivial 21-vertex component (S_idx = 0).
    S_idx = 0
    copy_verts = list(range(n3 + S_idx * n3, n3 + (S_idx + 1) * n3))
    new_verts = list(
        range(n3 * (1 + s3) + S_idx * s3, n3 * (1 + s3) + (S_idx + 1) * s3)
    )
    verts = copy_verts + new_verts
    if len(verts) != 21:
        raise ValueError(f"Expected 21 vertices, got {len(verts)}")

    sub_edges = induced_subgraph_edges(G4.edges, verts)
    n = len(verts)
    m = len(sub_edges)
    mc = maxcut_bruteforce(n, sub_edges)
    deletions = m - mc
    bound = isqrt(n)

    print("")
    print("Counterexample candidate (induced component of G4):")
    print(f"  n={n} m={m} MaxCut={mc} deletions=m-MaxCut={deletions} sqrt(n)={bound}")
    print(f"  violates sqrt bound? {deletions > bound}")

    return 1 if deletions > bound else 0


if __name__ == "__main__":
    raise SystemExit(main())
