from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import isqrt


@dataclass(frozen=True)
class Graph:
    n: int
    # Undirected simple graph edges, stored as (u, v) with u < v.
    edges: list[tuple[int, int]]


@dataclass(frozen=True)
class TwincutMeta:
    # Number of tree vertices (excluding branch vertices).
    tree_n: int
    # Tree vertices by level (0-based; level 0 is the root).
    tree_levels: list[list[int]]
    # Leaf vertex ids in the tree (i.e., last level).
    leaves: list[int]
    # Parent pointer for tree vertices (root maps to None).
    parent: dict[int, int | None]


def build_twincut_graphs(k_max: int) -> tuple[list[Graph], list[TwincutMeta]]:
    """
    Build the twincut graphs G_1..G_{k_max} from arXiv:2304.04296.

    Construction recap (Bonnet et al. 2023, Section 2):
      - G_1 is a single vertex.
      - For k>=2, G_k is the realization R(T_k, g_k) of a structured rooted tree:
          * T_k has (k-1) levels (root at level 1 in the paper).
          * Every node at level i<k-1 has |V(G_{i+1})| children.
          * The children of such a node induce a copy of G_{i+1}.
          * For every root-to-leaf branch, add a "branch vertex" adjacent to all
            tree vertices on that branch.
          * The parent-child edges of the tree are NOT edges of G_k.

    We use a deterministic vertex ordering:
      - Tree vertices are created level-by-level, left-to-right.
      - All branch vertices are created afterwards, in the order of the leaves.
    """

    if k_max < 1:
        raise ValueError("k_max must be >= 1")

    graphs: list[Graph] = [Graph(0, []) for _ in range(k_max + 1)]
    metas: list[TwincutMeta] = [
        TwincutMeta(tree_n=0, tree_levels=[], leaves=[], parent={})
        for _ in range(k_max + 1)
    ]

    graphs[1] = Graph(1, [])
    metas[1] = TwincutMeta(tree_n=1, tree_levels=[[0]], leaves=[0], parent={0: None})

    for k in range(2, k_max + 1):
        edges: set[tuple[int, int]] = set()

        tree_levels: list[list[int]] = [[0]]
        parent: dict[int, int | None] = {0: None}
        next_vid = 1

        # Create tree vertices and add "sibling edges" according to copies of G_{i+1}.
        # The tree has (k-1) levels, so we create levels 2..k-1 inclusive.
        for i in range(1, k - 1):
            prev_level = tree_levels[i - 1]
            child_graph = graphs[i + 1]
            child_n = child_graph.n

            new_level: list[int] = []
            for v in prev_level:
                off = next_vid
                next_vid += child_n
                for j in range(child_n):
                    parent[off + j] = v

                for a, b in child_graph.edges:
                    u = off + a
                    w = off + b
                    edges.add((u, w) if u < w else (w, u))

                new_level.extend(range(off, off + child_n))

            tree_levels.append(new_level)

        tree_n = next_vid
        leaves = tree_levels[-1]

        # Add one branch vertex per leaf, adjacent to all tree vertices on the branch.
        for leaf in leaves:
            b = next_vid
            next_vid += 1

            cur: int | None = leaf
            while cur is not None:
                edges.add((cur, b) if cur < b else (b, cur))
                cur = parent[cur]

        graphs[k] = Graph(next_vid, sorted(edges))
        metas[k] = TwincutMeta(
            tree_n=tree_n, tree_levels=tree_levels, leaves=leaves, parent=parent
        )

    return graphs, metas


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


def connected_components(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj: dict[int, list[int]] = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    seen: set[int] = set()
    comps: list[list[int]] = []
    for v in range(n):
        if v in seen:
            continue
        q = deque([v])
        seen.add(v)
        comp: list[int] = []
        while q:
            x = q.popleft()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        comps.append(comp)
    return comps


def maxcut_by_components(
    n: int, edges: list[tuple[int, int]], component_n_limit: int = 25
) -> int:
    """
    Exact MaxCut for a disconnected graph by summing exact MaxCut over components.

    For each connected component, we run `maxcut_gray` after re-indexing vertices.
    """

    comps = connected_components(n, edges)
    total = 0
    for comp in comps:
        if len(comp) > component_n_limit:
            raise ValueError(f"component too large for exact MaxCut: |V|={len(comp)}")
        sub_edges = induced_subgraph_edges(edges, comp)
        total += maxcut_gray(len(comp), sub_edges)
    return total


def main() -> int:
    graphs, metas = build_twincut_graphs(5)

    print("Twincut graphs from arXiv:2304.04296")
    for k in range(1, 5):
        G = graphs[k]
        m = len(G.edges)
        mc = maxcut_gray(G.n, G.edges)
        deletions = m - mc
        bound = isqrt(G.n)
        print(
            f"  G{k}: n={G.n} m={m} MaxCut={mc} ebip=m-MaxCut={deletions} sqrt(n)={bound}"
        )

    G4 = graphs[4]
    m4 = len(G4.edges)
    mc4 = maxcut_gray(G4.n, G4.edges)
    del4 = m4 - mc4
    bound4 = isqrt(G4.n)

    print("")
    print("Smallest counterexample found (G4 itself):")
    print(f"  n={G4.n} m={m4} MaxCut={mc4} ebip=m-MaxCut={del4} sqrt(n)={bound4}")
    print(f"  violates sqrt bound? {del4 > bound4}")

    # Bonus: exhibit many vertex-disjoint odd cycles despite the cutset≤2 structure.
    # In our canonical labeling of G4, its leaf set is exactly the tree vertices of level 3.
    # Inside G5 there are 10 disjoint copies of G4 as induced subgraphs (as sibling-sets).
    # Taking 3 such copies and keeping only the 10 "leaf" vertices of each yields 6 disjoint C5's.
    G5 = graphs[5]
    meta4 = metas[4]
    meta5 = metas[5]

    leaf_ids_in_G4 = (
        meta4.leaves
    )  # vertex ids in G4, used as indices in each embedded copy
    n4 = graphs[4].n

    # Children of the first 3 level-3 nodes form 3 disjoint copies of G4 in G5.
    selected: list[int] = []
    level4 = meta5.tree_levels[3]
    for j in range(3):
        off = level4[j * n4]  # start of the j-th sibling-block of size |V(G4)|
        selected.extend([off + t for t in leaf_ids_in_G4])

    H_edges = induced_subgraph_edges(G5.edges, selected)
    nH = len(selected)
    mH = len(H_edges)
    mcH = maxcut_by_components(nH, H_edges, component_n_limit=25)
    delH = mH - mcH
    boundH = isqrt(nH)

    print("")
    print("Cycle-packing witness (induced subgraph of G5):")
    print(f"  n={nH} m={mH} MaxCut={mcH} ebip=m-MaxCut={delH} sqrt(n)={boundH}")
    print(f"  violates sqrt bound? {delH > boundH}")
    print(
        f"  connected components sizes: {sorted(map(len, connected_components(nH, H_edges)))}"
    )

    return 1 if del4 > bound4 else 0


if __name__ == "__main__":
    raise SystemExit(main())
