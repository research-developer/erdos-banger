from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import isqrt
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class Graph:
    n: int
    # Undirected simple graph edges, stored as (u, v) with u < v.
    edges: list[tuple[int, int]]

    @property
    def m(self) -> int:
        return len(self.edges)


def normalize_edges(n: int, edges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Normalize to a sorted list of unique undirected edges with u < v.
    """

    norm: set[tuple[int, int]] = set()
    for u, v in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"edge out of range: ({u}, {v}) for n={n}")
        if u == v:
            continue
        a, b = (u, v) if u < v else (v, u)
        norm.add((a, b))
    return sorted(norm)


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


def maxcut_gray_witness(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """
    Exact MaxCut via Gray-code enumeration, returning a witness assignment.

    Returns `(best_cut, assignment_mask)` where bit `i` indicates whether vertex `i`
    is on side 1 of the cut. The last vertex is fixed to 0 to break symmetry.

    Suitable for n up to ~25.
    """

    if n <= 1:
        return 0, 0

    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    deg = [a.bit_count() for a in adj]

    best = 0
    best_g = 0
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

        if cut > best:
            best = cut
            best_g = g
        prev_g = g

    return best, best_g


def monochromatic_edges_for_assignment(
    edges: list[tuple[int, int]], assignment_mask: int
) -> list[tuple[int, int]]:
    """
    Return the edges whose endpoints are on the *same* side of the cut.

    Deleting these edges makes the graph bipartite with the given bipartition.
    """

    mono: list[tuple[int, int]] = []
    for u, v in edges:
        if (((assignment_mask >> u) ^ (assignment_mask >> v)) & 1) == 0:
            mono.append((u, v))
    return mono


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

    total = 0
    for comp in connected_components(n, edges):
        if len(comp) > component_n_limit:
            raise ValueError(f"component too large for exact MaxCut: |V|={len(comp)}")
        sub_edges = induced_subgraph_edges(edges, comp)
        total += maxcut_gray(len(comp), sub_edges)
    return total


def ebip(n: int, edges: list[tuple[int, int]]) -> int:
    """
    ebip(H) = |E(H)| - MaxCut(H).
    """

    return len(edges) - maxcut_gray(n, edges)


def ebip_witness(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """
    Return `(ebip, assignment_mask)` where `assignment_mask` witnesses MaxCut.

    The corresponding edge-deletion witness is
    `monochromatic_edges_for_assignment(edges, assignment_mask)`.
    """

    best_cut, assignment_mask = maxcut_gray_witness(n, edges)
    return len(edges) - best_cut, assignment_mask


def sqrt_bound(n: int) -> int:
    """
    Integer floor sqrt used in the repo scripts.
    """

    return isqrt(n)


def _adj_bitmasks(n: int, edges: list[tuple[int, int]]) -> list[int]:
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return adj


def chromatic_number_exact(n: int, edges: list[tuple[int, int]]) -> int:  # noqa: PLR0915
    """
    Exact chromatic number via DSATUR-style branch and bound.

    Intended for small graphs (n <= ~40); our use-case is n <= 25.
    """

    if n <= 1:
        return n

    adj = _adj_bitmasks(n, edges)
    deg = [a.bit_count() for a in adj]

    colors = [0] * n
    used_mask = [0] * n  # bit i means color i is used by a colored neighbor

    def greedy_upper_bound() -> int:
        order = sorted(range(n), key=lambda v: deg[v], reverse=True)
        max_color = 0
        masks = [0] * n
        for v in order:
            forb = masks[v]
            c = 1
            while forb & (1 << c):
                c += 1
            max_color = max(max_color, c)
            for u_bit in iter_bits(adj[v]):
                masks[u_bit] |= 1 << c
        return max_color

    def iter_bits(mask: int) -> Iterable[int]:
        while mask:
            lsb = mask & -mask
            yield (lsb.bit_length() - 1)
            mask ^= lsb

    best = greedy_upper_bound()

    def pick_vertex() -> int:
        # Choose uncolored vertex with max saturation degree, break ties by degree.
        best_v = -1
        best_sat = -1
        best_deg = -1
        for v in range(n):
            if colors[v] != 0:
                continue
            sat = used_mask[v].bit_count()
            if sat > best_sat or (sat == best_sat and deg[v] > best_deg):
                best_v = v
                best_sat = sat
                best_deg = deg[v]
        return best_v

    def dfs(colored: int, max_color: int) -> None:  # noqa: PLR0912
        nonlocal best
        if max_color >= best:
            return
        if colored == n:
            best = min(best, max_color)
            return

        v = pick_vertex()
        if v < 0:
            best = min(best, max_color)
            return

        forb = used_mask[v]

        # Try existing colors first.
        for c in range(1, max_color + 1):
            if forb & (1 << c):
                continue
            colors[v] = c
            changed: list[tuple[int, int]] = []
            for u in iter_bits(adj[v]):
                if colors[u] != 0:
                    continue
                old = used_mask[u]
                new = old | (1 << c)
                if new != old:
                    used_mask[u] = new
                    changed.append((u, old))

            dfs(colored + 1, max_color)

            for u, old in changed:
                used_mask[u] = old
            colors[v] = 0

        # Try using a new color.
        c_new = max_color + 1
        if c_new < best:
            colors[v] = c_new
            changed = []
            for u in iter_bits(adj[v]):
                if colors[u] != 0:
                    continue
                old = used_mask[u]
                new = old | (1 << c_new)
                if new != old:
                    used_mask[u] = new
                    changed.append((u, old))

            dfs(colored + 1, c_new)

            for u, old in changed:
                used_mask[u] = old
            colors[v] = 0

    dfs(0, 0)
    return best
