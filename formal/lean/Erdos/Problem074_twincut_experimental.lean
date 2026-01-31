/-
Problem 74: Erdős Problem #74 - TWINCUT GRAPH APPROACH

Status: REFUTED (2026-01-31)
Prize: $500

This file attempts to solve Problem 74 using twincut graphs as the candidate construction.

Twincut graphs (Bonnet, Bourneuf, Duron, Geniet, Thomassé, Trotignon 2023) are:
- Triangle-free (no 3-cycles)
- Have unbounded chromatic number: χ(Gₖ) = k
- Hereditary class (induced subgraphs stay in the class)
- Key structural constraint: Every graph either has twins OR vertex cutset ≤ 2

KEY HYPOTHESIS (FALSE): The small vertex cutset property (≤2) might prevent packing
many vertex-disjoint odd cycles, which is exactly what killed the Burling approach.

WHY BURLING FAILED: The Burling NEXT-B construction creates disjoint copies,
allowing Θ(n) vertex-disjoint odd cycles to be packed in n vertices.
This fundamentally violates √n bound (need ≥ n edge deletions, not √n).

WHY TWINCUT DOES NOT WORK: G₄ already violates the √n bound.
See `scripts/twincut_sqrt_test.py` for an exact MaxCut computation:
  - n = 23, m = 41, MaxCut = 34, ebip = 7, Nat.sqrt 23 = 4, so 7 > 4.

Reference: arXiv:2304.04296 "A tamed family of triangle-free graphs with unbounded chromatic number"
-/

import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Subgraph
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Finset.Powerset

open Filter SimpleGraph
open scoped BigOperators

namespace Erdos.Problem074.Twincut

/-!
## Core Definitions (shared with other P74 files)
-/

universe u
variable {V : Type u}

def SimpleGraph.edgeDistancesToBipartite {G : SimpleGraph V} (A : G.Subgraph) : Set ℕ :=
  { (E.ncard) | (E : Set (Sym2 V)) (_ : E ⊆ A.edgeSet) (_ : IsBipartite (A.deleteEdges E).coe)}

noncomputable def SimpleGraph.minEdgeDistToBipartite {G : SimpleGraph V} (A : G.Subgraph) : ℕ :=
  sInf <| SimpleGraph.edgeDistancesToBipartite A

def SimpleGraph.subgraphEdgeDistsToBipartite (G : SimpleGraph V) (n : ℕ) : Set ℕ :=
  { (SimpleGraph.minEdgeDistToBipartite A) |
    (A : Subgraph G) (_ : A.verts.ncard = n) (_ : A.verts.Finite) }

noncomputable def SimpleGraph.maxSubgraphEdgeDistToBipartite
    (G : SimpleGraph V) (n : ℕ) : ℕ := sSup <| SimpleGraph.subgraphEdgeDistsToBipartite G n

/-!
## Twincut Class Definition

From arXiv:2304.04296, the twincut class is defined by a structural decomposition property.

**Definition:** A graph G is in the twincut class if one of the following holds:
1. G has at most 2 vertices
2. G has a pair of non-adjacent twins (vertices with identical neighborhoods)
3. G has an edgeless vertex cutset of size at most 2 that separates G into
   smaller graphs in the twincut class

The key property: Every member either has twins or has connectivity ≤ 2.
-/

/--
Two vertices are twins if they have exactly the same neighbors (not adjacent to each other).
-/
def areTwins (G : SimpleGraph V) (u v : V) : Prop :=
  u ≠ v ∧ ¬G.Adj u v ∧ ∀ w : V, w ≠ u → w ≠ v → (G.Adj u w ↔ G.Adj v w)

/--
A graph has twins if some pair of vertices are twins.
-/
def hasTwins (G : SimpleGraph V) : Prop :=
  ∃ u v : V, areTwins G u v

/--
An edgeless cutset is a set of vertices with no edges between them.
-/
def isEdgelessCutset (G : SimpleGraph V) (S : Set V) : Prop :=
  ∀ u v : V, u ∈ S → v ∈ S → ¬G.Adj u v

/--
S is a vertex cutset if removing S disconnects the graph:
there exist u, v not in S that are reachable in G but not in G \ S.
-/
def isVertexCutset (G : SimpleGraph V) (S : Set V) : Prop :=
  ∃ u v : V, u ∉ S ∧ v ∉ S ∧ G.Reachable u v ∧
    ¬∃ (p : G.Walk u v), ∀ w ∈ p.support, w ∉ S

/--
A graph has a small edgeless cutset if it has an edgeless cutset of size ≤ 2.
-/
def hasSmallEdgelessCutset (G : SimpleGraph V) : Prop :=
  ∃ S : Set V, S.ncard ≤ 2 ∧ isEdgelessCutset G S ∧ isVertexCutset G S

/-!
## Twincut Graph Construction

The twincut class is built recursively. We axiomatize the existence of the
sequence and its key properties.
-/

/--
Vertices of the k-th twincut graph.
-/
axiom TwincutVertex : ℕ → Type

/--
The adjacency relation for twincut graphs.
-/
axiom TwincutGraphAdj : (k : ℕ) → TwincutVertex k → TwincutVertex k → Prop
axiom TwincutGraphAdj_symm : ∀ k u v, TwincutGraphAdj k u v → TwincutGraphAdj k v u
axiom TwincutGraphAdj_loopless : ∀ k v, ¬TwincutGraphAdj k v v

def TwincutGraph (k : ℕ) : SimpleGraph (TwincutVertex k) where
  Adj := TwincutGraphAdj k
  symm := TwincutGraphAdj_symm k
  loopless := TwincutGraphAdj_loopless k

/-!
## Key Properties of Twincut Graphs

From arXiv:2304.04296, twincut graphs satisfy:
-/

/--
Twincut graphs are triangle-free (same as Burling).
-/
axiom twincut_triangle_free (k : ℕ) : (TwincutGraph k).CliqueFree 3

/--
The k-th twincut graph has chromatic number exactly k (same growth as Burling).
-/
axiom twincut_chromatic_number (k : ℕ) (hk : k ≥ 1) :
    (TwincutGraph k).chromaticNumber = k

/--
**THE KEY STRUCTURAL PROPERTY**

Every non-trivial twincut graph either:
1. Has a pair of non-adjacent twins, OR
2. Has an edgeless vertex cutset of size at most 2

This is what distinguishes twincut from Burling!
-/
axiom twincut_structure (k : ℕ) (hk : k ≥ 3) :
    hasTwins (TwincutGraph k) ∨ hasSmallEdgelessCutset (TwincutGraph k)

/--
Twincut graphs are edge-critical: removing any edge decreases chromatic number.
-/
axiom twincut_edge_critical (k : ℕ) (hk : k ≥ 2) (e : Sym2 (TwincutVertex k))
    (he : e ∈ (TwincutGraph k).edgeSet) :
    ((TwincutGraph k).deleteEdges {e}).chromaticNumber < (TwincutGraph k).chromaticNumber

/-!
## The Anti-Packing Hypothesis

The key insight: If every graph has cutset ≤ 2, then vertex-disjoint odd cycles
cannot be isolated from each other. They must share vertices/edges near the cutset.

Conjecture: In any n-vertex twincut subgraph, there are at most O(√n) vertex-disjoint odd cycles.
-/

/--
Count of vertex-disjoint odd cycles in a graph.
-/
def maxDisjointOddCycles (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj] : ℕ := sorry

/--
**CORE HYPOTHESIS**: Small cutset implies bounded disjoint odd cycles.

If G has cutset ≤ 2 (or twins), then the number of vertex-disjoint odd cycles
in any n-vertex induced subgraph is at most c√n for some constant c.

NOTE: This is false for the twincut family from arXiv:2304.04296 (see the header
counterexample and `formal/lean/Erdos/Problem074_TWINCUT_RESOURCES.md`).
-/
axiom small_cutset_bounds_odd_cycles (G : SimpleGraph V) [Fintype V] [DecidableRel G.Adj]
    (h : hasTwins G ∨ hasSmallEdgelessCutset G) (n : ℕ) (hn : Fintype.card V = n) :
    maxDisjointOddCycles G ≤ Nat.sqrt n

/-!
## The Prize Question

If we can prove this theorem, we win $500!
-/

/--
**THE $500 QUESTION**

Conjecture (FALSE): Twincut graphs satisfy a sublinear edge-deletion bound.

Strategy:
1. Use twincut_structure to get twins or small cutset
2. Use small_cutset_bounds_odd_cycles to bound disjoint odd cycles
3. Conclude that √n edge deletions suffice (one per disjoint odd cycle)
-/
def twincut_sublinear_conjecture : Prop :=
  ∀ k : ℕ, ∀ n : ℕ,
    SimpleGraph.maxSubgraphEdgeDistToBipartite (TwincutGraph k) n ≤ Nat.sqrt n

/--
Stronger version: the infinite disjoint union satisfies the bound.
-/
def twincut_infinite_satisfies_sqrt : Prop :=
  ∃ (W : Type) (G : SimpleGraph W),
    G.chromaticNumber = ⊤ ∧
    ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n

/-!
## Proof Attempt

The strategy:
1. For any n-vertex induced subgraph H of a twincut graph
2. H inherits the twincut property (twins or small cutset)
3. Therefore H has ≤ √n vertex-disjoint odd cycles
4. Deleting one edge per cycle makes H bipartite
5. QED: √n edge deletions suffice
-/

-- Helper: hereditary property (induced subgraphs are also twincut)
axiom twincut_hereditary (k : ℕ) (S : Set (TwincutVertex k)) :
    let H := (TwincutGraph k).induce S
    hasTwins H ∨ hasSmallEdgelessCutset H ∨ S.ncard ≤ 2

-- Main theorem attempt
theorem twincut_sublinear_attempt :
    ∀ k n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (TwincutGraph k) n ≤ Nat.sqrt n := by
  intro k n
  -- Strategy:
  -- 1. Take any n-vertex induced subgraph H
  -- 2. By twincut_hereditary, H has twins or small cutset (or is tiny)
  -- 3. By small_cutset_bounds_odd_cycles, H has ≤ √n disjoint odd cycles
  -- 4. Deleting one edge from each odd cycle makes H bipartite
  -- 5. Therefore minEdgeDistToBipartite H ≤ √n
  sorry

/-!
## Next Steps

### Computational Testing (DONE)
1. Implemented twincut graph generator in Python from arXiv:2304.04296
2. Tested √n bound on G₄: **fails** (G₄ itself violates √n)
3. Documented in `formal/lean/Erdos/Problem074_TWINCUT_RESOURCES.md`

### Theoretical Analysis
1. (Lesson) Cutset ≤ 2 does not prevent packing many vertex-disjoint odd cycles
2. Find the next candidate graph family for Problem #74

### Key Questions
- What stronger structural property would actually prevent linear odd-cycle packing?
- Can we enforce global overlap/bottlenecks for odd cycles?

### References
- arXiv:2304.04296 (main paper)
- Problem074_TWINCUT_RESOURCES.md (research notes)
-/

/-!
## Session Log

### 2026-01-30
- Created Problem074_twincut.lean (clean template)
- Created Problem074_twincut_experimental.lean (this file, for active work)
- Axiomatized key twincut properties from arXiv:2304.04296
- Defined twins, edgeless cutset, vertex cutset concepts
- Set up proof strategy for twincut_sublinear_attempt
- Ready for computational testing before full formal proof

### 2026-01-31
- Implemented the twincut construction (structured-tree realization) in `scripts/twincut_sqrt_test.py`.
- Found a direct √n violation already in G₄: `n=23, m=41, MaxCut=34, ebip=7, Nat.sqrt 23=4`.
- Marked the twincut approach as refuted for the √n edge-deletion bound.

### TODO
- [x] Implement twincut graph generator in Python (`scripts/twincut_sqrt_test.py`)
- [x] Test √n bound empirically on G₄ (fails)
- [ ] Find next candidate graph family
-/

end Erdos.Problem074.Twincut
