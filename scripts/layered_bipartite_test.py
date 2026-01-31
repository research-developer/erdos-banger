#!/usr/bin/env python3
"""
Layered Bipartite Construction for Erdős Problem 74

This is a fundamentally different approach from Hasse diagrams:
- Graph G = E1 U E2 U E3 U ... (union of bipartite layers)
- Each Ei is bipartite w.r.t. cut Pi (partition by bit i)
- Density pi decays fast (exponentially or super-exponentially)

KEY INSIGHT (Cauchy-Schwarz for constant = 1):
For any subset S, pick best witness cut Πᵢ*. Bad edges are from other layers.
If layer j contributes ≤ aⱼ√|S| bad edges with Σaⱼ² ≤ 1, then:
  |D(S)| ≤ Σaⱼ√|S| ≤ √|S| · √(Σaⱼ²) ≤ √|S|

Run: uv run python scripts/layered_bipartite_test.py
"""

from __future__ import annotations

import contextlib
import random
import sys
from collections import deque
from dataclasses import dataclass
from math import isqrt, sqrt
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


sys.path.insert(0, "scripts")
from ebip_utils import (
    chromatic_number_exact,
    maxcut_gray,
)


@dataclass
class LayeredBipartiteGraph:
    """A graph built as union of bipartite layers."""

    num_vertices: int
    num_layers: int
    # layers[i] = list of edges in layer i
    layers: list[list[tuple[int, int]]]
    # densities[i] = density parameter for layer i
    densities: list[float]

    @property
    def all_edges(self) -> list[tuple[int, int]]:
        """Union of all layer edges."""
        seen: set[tuple[int, int]] = set()
        for layer in self.layers:
            for u, v in layer:
                e = (min(u, v), max(u, v))
                seen.add(e)
        return sorted(seen)

    @property
    def num_edges(self) -> int:
        return len(self.all_edges)


def bit_partition(v: int, bit: int) -> int:
    """Return 0 or 1 based on bit position of vertex v."""
    return (v >> bit) & 1


def build_layered_bipartite(
    n: int,
    num_layers: int,
    density_schedule: Callable[[int], float],
    seed: int | None = None,
) -> LayeredBipartiteGraph:
    """
    Build a layered bipartite graph.

    Args:
        n: Number of vertices (should be power of 2 for clean bit partitions)
        num_layers: Number of layers L
        density_schedule: Function i -> p_i (edge probability for layer i)
        seed: Random seed for reproducibility

    Returns:
        LayeredBipartiteGraph with the specified structure
    """
    if seed is not None:
        random.seed(seed)

    densities = [density_schedule(i) for i in range(num_layers)]
    layers: list[list[tuple[int, int]]] = []

    for i in range(num_layers):
        p_i = densities[i]
        layer_edges: list[tuple[int, int]] = []

        # Πᵢ partitions vertices by bit i
        # Layer i has edges ONLY between vertices with different bit i
        for u in range(n):
            for v in range(u + 1, n):
                # u and v are on opposite sides of cut Πᵢ
                if bit_partition(u, i) != bit_partition(v, i) and random.random() < p_i:  # noqa: S311
                    layer_edges.append((u, v))

        layers.append(layer_edges)

    return LayeredBipartiteGraph(
        num_vertices=n,
        num_layers=num_layers,
        layers=layers,
        densities=densities,
    )


# === Density Schedules ===


def exponential_density(c: float, decay: float = 2.0) -> Callable[[int], float]:
    """p_i = min(1, c * decay^{-power*i}) with default power=2."""

    power = 2.0

    def schedule(i: int) -> float:
        return min(1.0, c * (decay ** (-power * i)))

    return schedule


def exponential_density_power(
    c: float, power: float, decay: float = 2.0
) -> Callable[[int], float]:
    """p_i = min(1, c * decay^{-power*i})"""

    def schedule(i: int) -> float:
        return min(1.0, c * (decay ** (-power * i)))

    return schedule


def super_exp_density(c: float) -> Callable[[int], float]:
    """p_i = min(1, c * 2^{-2^i})"""

    def schedule(i: int) -> float:
        return min(1.0, c * (2.0 ** (-(2**i))))

    return schedule


def shifted_super_exp_density(c: float, shift: int) -> Callable[[int], float]:
    """p_i = min(1, c * 2^{-2^(i+shift)})"""

    def schedule(i: int) -> float:
        return min(1.0, c * (2.0 ** (-(2 ** (i + shift)))))

    return schedule


def cutoff_density(c: float, cutoff: int, decay: float = 2.0) -> Callable[[int], float]:
    """p_i = min(1, c * decay^{-2i}) for i <= cutoff, else 0"""

    def schedule(i: int) -> float:
        if i > cutoff:
            return 0.0
        return min(1.0, c * (decay ** (-2 * i)))

    return schedule


# === Analysis Functions ===


def induced_subgraph_edges(
    all_edges: list[tuple[int, int]], subset: list[int]
) -> list[tuple[int, int]]:
    """Get edges of induced subgraph on subset, reindexed to 0..len(subset)-1."""
    idx = {v: i for i, v in enumerate(subset)}
    vset = set(subset)
    result: list[tuple[int, int]] = []
    for u, v in all_edges:
        if u in vset and v in vset:
            result.append((idx[u], idx[v]))
    return result


def compute_ebip(n: int, edges: list[tuple[int, int]]) -> int:
    """ebip = |E| - MaxCut"""
    if n <= 1 or not edges:
        return 0
    mc = maxcut_gray(n, edges)
    return len(edges) - mc


def _cycle_vertices_to_edges(cycle: list[int]) -> set[tuple[int, int]]:
    cycle_edges: set[tuple[int, int]] = set()
    for i in range(len(cycle)):
        u = cycle[i]
        v = cycle[(i + 1) % len(cycle)]
        cycle_edges.add((min(u, v), max(u, v)))
    return cycle_edges


def _find_one_odd_cycle(n: int, edges: list[tuple[int, int]]) -> list[int] | None:
    """
    Find a single odd cycle (as a vertex list) via BFS 2-coloring.

    This is intended as a fast *witness* for non-bipartiteness, not an exhaustive
    odd-cycle enumerator.
    """
    if n <= 2 or not edges:
        return None

    adj: list[list[int]] = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    color = [-1] * n
    parent = [-1] * n

    for start in range(n):
        if color[start] != -1:
            continue
        color[start] = 0
        parent[start] = -1
        q: deque[int] = deque([start])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if color[v] == -1:
                    color[v] = 1 - color[u]
                    parent[v] = u
                    q.append(v)
                elif v != parent[u] and color[v] == color[u]:
                    # Found an odd cycle using the conflict edge (u, v).
                    anc_u: set[int] = set()
                    x = u
                    while x != -1:
                        anc_u.add(x)
                        x = parent[x]

                    lca = v
                    while lca not in anc_u:
                        lca = parent[lca]

                    path_u: list[int] = []
                    x = u
                    while x != lca:
                        path_u.append(x)
                        x = parent[x]
                    path_u.append(lca)

                    path_v: list[int] = []
                    y = v
                    while y != lca:
                        path_v.append(y)
                        y = parent[y]
                    path_v.append(lca)

                    # This path starts at u and ends at v, so the closing edge v-u
                    # is exactly the conflict edge.
                    cycle_vertices = path_u + list(reversed(path_v[:-1]))
                    return cycle_vertices

    return None


def odd_cycle_packing_lower_bound(
    n: int, edges: list[tuple[int, int]], stop_after: int | None = None
) -> int:
    """
    Greedy lower bound on Ve(G): repeatedly find an odd cycle and remove its edges.

    If `stop_after` is set, stop once the packing reaches that size.
    """
    remaining: set[tuple[int, int]] = {(min(u, v), max(u, v)) for u, v in edges}
    count = 0
    while remaining:
        cycle = _find_one_odd_cycle(n, list(remaining))
        if cycle is None:
            break
        cycle_edges = _cycle_vertices_to_edges(cycle)
        remaining -= cycle_edges
        count += 1
        if stop_after is not None and count >= stop_after:
            break
    return count


def odd_cycle_packing_witness(
    n: int, edges: list[tuple[int, int]], stop_after: int | None = None
) -> list[list[int]]:
    """
    Greedy edge-disjoint odd-cycle packing witness: returns the cycles found.

    Each cycle is returned as a list of vertices in cyclic order; cycles are
    edge-disjoint by construction.
    """
    remaining: set[tuple[int, int]] = {(min(u, v), max(u, v)) for u, v in edges}
    cycles: list[list[int]] = []
    while remaining:
        cycle = _find_one_odd_cycle(n, list(remaining))
        if cycle is None:
            break
        remaining -= _cycle_vertices_to_edges(cycle)
        cycles.append(cycle)
        if stop_after is not None and len(cycles) >= stop_after:
            break
    return cycles


def compute_canonical_deletion_set(
    G: LayeredBipartiteGraph, subset: list[int]
) -> tuple[int, int]:
    """
    Compute the canonical deletion set size for a subset.

    For each possible witness cut i, count edges from OTHER layers
    that fall inside one side of Πᵢ. Return the minimum.

    Returns: (best_witness_idx, deletion_set_size)
    """
    if len(subset) <= 1:
        return (0, 0)

    vset = set(subset)

    best_i = 0
    best_count = float("inf")

    for witness_i in range(G.num_layers):
        # Count "bad edges" from layers j != witness_i
        # Bad = both endpoints on same side of cut Πᵢ
        bad_count = 0
        for j, layer in enumerate(G.layers):
            if j == witness_i:
                continue
            for u, v in layer:
                # Check if u and v are on same side of witness cut
                if (
                    u in vset
                    and v in vset
                    and bit_partition(u, witness_i) == bit_partition(v, witness_i)
                ):
                    bad_count += 1

        if bad_count < best_count:
            best_count = bad_count
            best_i = witness_i

    return (best_i, int(best_count))


def analyze_graph(  # noqa: PLR0915
    G: LayeredBipartiteGraph,
    max_subset_size: int = 25,
    num_samples: int = 200,
    exact_ebip_max_k: int = 18,
    exact_ebip_budget: int = 12,
    stop_on_violation: bool = True,
    seed: int | None = None,
) -> dict:
    """
    Analyze a layered bipartite graph for the √n bound.

    Returns dict with:
        - worst_ebip_ratio: max(ebip/√n) over sampled subsets
        - worst_canonical_ratio: max(|D(S)|/√n) over sampled subsets
        - worst_subset: the subset achieving worst ebip ratio
        - chromatic: chromatic number (if computable)
    """
    if seed is not None:
        random.seed(seed)

    all_edges = G.all_edges
    n = G.num_vertices

    worst_ebip_ratio = 0.0
    worst_canonical_ratio = 0.0
    worst_ve_ratio = 0.0
    worst_subset: list[int] = []
    worst_k = 0
    worst_ebip = 0
    worst_ve_subset: list[int] = []
    worst_ve_k = 0
    worst_ve = 0

    violating_subset: list[int] = []
    violating_k = 0
    violating_ve = 0
    violating_ebip: int | None = None
    violating_canonical: int | None = None
    violating_cycles: list[list[int]] | None = None
    exact_ebip_checks = 0

    for _ in range(num_samples):
        # Sample random subset size
        k = random.randint(5, min(max_subset_size, n))  # noqa: S311
        subset = random.sample(range(n), k)
        sqrt_k = isqrt(k)

        # Build induced subgraph once.
        sub_edges = induced_subgraph_edges(all_edges, subset)

        # Fast obstruction: Ve(G[S]) = max edge-disjoint odd cycles.
        # Always ebip(G[S]) >= Ve(G[S]).
        ve = odd_cycle_packing_lower_bound(k, sub_edges, stop_after=sqrt_k + 1)
        if sqrt_k > 0:
            ve_ratio = ve / sqrt(k)
            if ve_ratio > worst_ve_ratio:
                worst_ve_ratio = ve_ratio
                worst_ve_subset = subset
                worst_ve_k = k
                worst_ve = ve

        if ve > sqrt_k and not violating_subset:
            violating_subset = subset
            violating_k = k
            violating_ve = ve
            _, violating_canonical = compute_canonical_deletion_set(G, subset)
            violating_cycles = odd_cycle_packing_witness(
                k, sub_edges, stop_after=sqrt_k + 1
            )
            if stop_on_violation:
                break

        # Compute exact ebip only for small k and within a per-graph budget.
        ebip_val: int | None = None
        if k <= exact_ebip_max_k and exact_ebip_checks < exact_ebip_budget:
            ebip_val = compute_ebip(k, sub_edges)
            exact_ebip_checks += 1

        if sqrt_k > 0 and ebip_val is not None:
            ratio = ebip_val / sqrt(k)
            if ratio > worst_ebip_ratio:
                worst_ebip_ratio = ratio
                worst_subset = subset
                worst_k = k
                worst_ebip = ebip_val

        # Compute canonical deletion set size
        _, canon_size = compute_canonical_deletion_set(G, subset)
        if sqrt_k > 0:
            canon_ratio = canon_size / sqrt(k)
            worst_canonical_ratio = max(worst_canonical_ratio, canon_ratio)

    # Compute chromatic number for small graphs
    chromatic = None
    if n <= 32:
        with contextlib.suppress(Exception):
            chromatic = chromatic_number_exact(n, all_edges)

    return {
        "num_vertices": n,
        "num_edges": len(all_edges),
        "num_layers": G.num_layers,
        "worst_ebip_ratio": worst_ebip_ratio,
        "worst_canonical_ratio": worst_canonical_ratio,
        "worst_ve_ratio": worst_ve_ratio,
        "worst_k": worst_k,
        "worst_ebip": worst_ebip,
        "worst_subset": worst_subset,
        "worst_ve_k": worst_ve_k,
        "worst_ve": worst_ve,
        "worst_ve_subset": worst_ve_subset,
        "violating_k": violating_k,
        "violating_ve": violating_ve,
        "violating_ebip": violating_ebip,
        "violating_canonical": violating_canonical,
        "violating_cycles": violating_cycles,
        "violating_subset": violating_subset,
        "exact_ebip_checks": exact_ebip_checks,
        "chromatic": chromatic,
        "densities": G.densities,
    }


def test_schedule(
    schedule_name: str,
    density_fn: Callable[[int], float],
    n_values: list[int] | None = None,
    num_layers: int = 6,
    seed: int = 42,
    num_samples: int = 80,
) -> None:
    """Test a density schedule across multiple graph sizes."""
    if n_values is None:
        n_values = [32, 64, 128]
    print(f"\n{'=' * 60}")
    print(f"Testing schedule: {schedule_name}")
    print(f"{'=' * 60}")

    for n in n_values:
        G = build_layered_bipartite(n, num_layers, density_fn, seed=seed)
        result = analyze_graph(
            G,
            max_subset_size=min(25, n - 1),
            num_samples=num_samples,
            seed=seed,
        )

        print(f"\nn={n}, L={num_layers}, |E|={result['num_edges']}")
        print(f"  Densities: {[f'{d:.4f}' for d in result['densities'][:4]]}...")
        certified_ratio = max(result["worst_ebip_ratio"], result["worst_ve_ratio"])
        print(
            f"  Worst ebip/√n ratio (exact, partial): {result['worst_ebip_ratio']:.4f}"
        )
        print(f"  Worst canonical/√n ratio: {result['worst_canonical_ratio']:.4f}")
        print(f"  Worst Ve/√n ratio: {result['worst_ve_ratio']:.4f} (lower bound)")
        print(f"  Worst certified ratio: {certified_ratio:.4f}")
        print(f"  Exact ebip checks: {result['exact_ebip_checks']}/{num_samples}")
        print(
            f"  Worst case: k={result['worst_k']}, ebip={result['worst_ebip']}, √k={isqrt(result['worst_k'])}"
        )
        print(
            f"  Worst Ve case: k={result['worst_ve_k']}, Ve≥{result['worst_ve']}, √k={isqrt(result['worst_ve_k'])}"
        )
        if result["violating_k"]:
            details = [
                f"k={result['violating_k']}",
                f"Ve≥{result['violating_ve']}",
                f"canonical={result['violating_canonical']}",
                f"√k={isqrt(result['violating_k'])}",
            ]
            if result["violating_ebip"] is not None:
                details.insert(2, f"ebip={result['violating_ebip']}")
            print(f"  Ve obstruction found: {', '.join(details)}")
            print(f"  Violating subset (vertex ids): {result['violating_subset']}")
            if result["violating_cycles"] is not None:
                cycles_orig = [
                    [result["violating_subset"][i] for i in cyc]
                    for cyc in result["violating_cycles"]
                ]
                cycle_lens = [len(cyc) for cyc in cycles_orig]
                print(f"  Packed odd cycles (lengths): {cycle_lens}")
                print(f"  Packed odd cycles (vertex ids): {cycles_orig}")
        if result["chromatic"]:
            print(f"  χ(G) = {result['chromatic']}")

        # Check if we're hitting constant = 1
        if certified_ratio <= 1.0 and not result["violating_k"]:
            print("  ✓ No sampled violations (not exhaustive).")
        else:
            print(
                "  ✗ Sampled violation or certified ratio > 1 (refutes this instance)."
            )


def main() -> None:
    print("Layered Bipartite Construction for Erdős Problem 74")
    print("=" * 60)
    print("Testing if union of bipartite layers can achieve ebip ≤ √n")
    print()

    # Test different density schedules
    schedules = [
        ("Exponential c=0.5", exponential_density(0.5)),
        ("Exponential c=0.3", exponential_density(0.3)),
        ("Exponential c=0.2", exponential_density(0.2)),
        ("Exponential power=6 c=0.8", exponential_density_power(0.8, power=6)),
        ("Exponential power=8 c=1.0", exponential_density_power(1.0, power=8)),
        ("Super-exp c=0.5", super_exp_density(0.5)),
        ("Super-exp c=0.3", super_exp_density(0.3)),
        ("Shifted super-exp shift=1 c=0.8", shifted_super_exp_density(0.8, shift=1)),
        ("Shifted super-exp shift=2 c=1.0", shifted_super_exp_density(1.0, shift=2)),
        ("Cutoff c=0.5, I=3", cutoff_density(0.5, cutoff=3)),
        ("Cutoff c=0.3, I=4", cutoff_density(0.3, cutoff=4)),
    ]

    for name, schedule in schedules:
        test_schedule(name, schedule, n_values=[32, 64], num_layers=6, num_samples=80)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("If any schedule shows ratio → 1.0 as n increases: PROMISING")
    print("If all schedules show ratio > 1.0 consistently: try other parameters")
    print("If ratio increases with n: construction is fundamentally broken")


if __name__ == "__main__":
    main()
