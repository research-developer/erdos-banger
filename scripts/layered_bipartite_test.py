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
from dataclasses import dataclass
from math import isqrt, sqrt
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


sys.path.insert(0, "scripts")
from ebip_utils import chromatic_number_exact, maxcut_gray


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
    """p_i = c * decay^{-2i}"""

    def schedule(i: int) -> float:
        return c * (decay ** (-2 * i))

    return schedule


def super_exp_density(c: float) -> Callable[[int], float]:
    """p_i = c * 2^{-2^i}"""

    def schedule(i: int) -> float:
        return c * (2.0 ** (-(2**i)))

    return schedule


def cutoff_density(c: float, cutoff: int, decay: float = 2.0) -> Callable[[int], float]:
    """p_i = c * decay^{-2i} for i <= cutoff, else 0"""

    def schedule(i: int) -> float:
        if i > cutoff:
            return 0.0
        return c * (decay ** (-2 * i))

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


def analyze_graph(
    G: LayeredBipartiteGraph,
    max_subset_size: int = 25,
    num_samples: int = 200,
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
    worst_subset: list[int] = []
    worst_k = 0
    worst_ebip = 0

    for _ in range(num_samples):
        # Sample random subset size
        k = random.randint(5, min(max_subset_size, n))  # noqa: S311
        subset = random.sample(range(n), k)

        # Compute ebip for induced subgraph
        sub_edges = induced_subgraph_edges(all_edges, subset)
        ebip = compute_ebip(k, sub_edges)
        sqrt_k = isqrt(k)

        if sqrt_k > 0:
            ratio = ebip / sqrt(k)
            if ratio > worst_ebip_ratio:
                worst_ebip_ratio = ratio
                worst_subset = subset
                worst_k = k
                worst_ebip = ebip

        # Compute canonical deletion set size
        _, canon_size = compute_canonical_deletion_set(G, subset)
        if sqrt_k > 0:
            canon_ratio = canon_size / sqrt(k)
            worst_canonical_ratio = max(worst_canonical_ratio, canon_ratio)

    # Compute chromatic number for small graphs
    chromatic = None
    if n <= 30:
        with contextlib.suppress(Exception):
            chromatic = chromatic_number_exact(n, all_edges)

    return {
        "num_vertices": n,
        "num_edges": len(all_edges),
        "num_layers": G.num_layers,
        "worst_ebip_ratio": worst_ebip_ratio,
        "worst_canonical_ratio": worst_canonical_ratio,
        "worst_k": worst_k,
        "worst_ebip": worst_ebip,
        "worst_subset": worst_subset,
        "chromatic": chromatic,
        "densities": G.densities,
    }


def test_schedule(
    schedule_name: str,
    density_fn: Callable[[int], float],
    n_values: list[int] | None = None,
    num_layers: int = 6,
    seed: int = 42,
) -> None:
    """Test a density schedule across multiple graph sizes."""
    if n_values is None:
        n_values = [32, 64, 128]
    print(f"\n{'=' * 60}")
    print(f"Testing schedule: {schedule_name}")
    print(f"{'=' * 60}")

    for n in n_values:
        G = build_layered_bipartite(n, num_layers, density_fn, seed=seed)
        result = analyze_graph(G, max_subset_size=min(25, n - 1), seed=seed)

        print(f"\nn={n}, L={num_layers}, |E|={result['num_edges']}")
        print(f"  Densities: {[f'{d:.4f}' for d in result['densities'][:4]]}...")
        print(f"  Worst ebip/√n ratio: {result['worst_ebip_ratio']:.4f}")
        print(f"  Worst canonical/√n ratio: {result['worst_canonical_ratio']:.4f}")
        print(
            f"  Worst case: k={result['worst_k']}, ebip={result['worst_ebip']}, √k={isqrt(result['worst_k'])}"
        )
        if result["chromatic"]:
            print(f"  χ(G) = {result['chromatic']}")

        # Check if we're hitting constant = 1
        if result["worst_ebip_ratio"] <= 1.0:
            print("  ✓ PASSES strict √n bound!")
        elif result["worst_ebip_ratio"] <= 1.1:
            print("  ~ Close to √n (ratio < 1.1)")
        else:
            print("  ✗ Violates √n bound (ratio > 1.1)")


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
        ("Super-exp c=0.5", super_exp_density(0.5)),
        ("Super-exp c=0.3", super_exp_density(0.3)),
        ("Cutoff c=0.5, I=3", cutoff_density(0.5, cutoff=3)),
        ("Cutoff c=0.3, I=4", cutoff_density(0.3, cutoff=4)),
    ]

    for name, schedule in schedules:
        test_schedule(name, schedule, n_values=[32, 64], num_layers=6)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("If any schedule shows ratio → 1.0 as n increases: PROMISING")
    print("If all schedules show ratio > 1.0 consistently: try other parameters")
    print("If ratio increases with n: construction is fundamentally broken")


if __name__ == "__main__":
    main()
