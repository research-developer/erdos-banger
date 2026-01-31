/-
Problem 74: Erdős Problem #74 - BURLING GRAPH APPROACH (EXPERIMENTAL)

Status: EXPERIMENTAL - Active development
Prize: $500

This is our working copy for attacking Problem 74 via Burling graphs.
The goal is to either:
1. PROVE the √n bound holds for Burling graphs (wins $500!)
2. DISPROVE it (rules out Burling as a candidate)
3. Prove intermediate results that inform the approach

Burling graphs (1965) are:
- Triangle-free (no 3-cycles)
- Have unbounded chromatic number: χ(B_k) = k
- Intersection graphs of axis-aligned boxes in ℝ³
- The minimal hereditary class with unbounded χ (besides complete graphs)

KEY HYPOTHESIS: Being triangle-free might make Burling graphs "almost bipartite" in the
edge-deletion sense, since only 5-cycles and longer can obstruct bipartiteness.

Reference: https://arxiv.org/abs/1703.07871 (Burling graphs, chromatic number, and orthogonal tree-decompositions)
-/

import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Combinatorics.SimpleGraph.Connectivity.WalkCounting
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Finset.Powerset

open Filter SimpleGraph
open scoped BigOperators

namespace Erdos.Problem074.BurlingExperimental

/-!
## Core Definitions (from Problem074_experimental.lean)
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
## Useful Lemmas (proved)
-/

theorem SimpleGraph.edgeDistancesToBipartite_nonempty {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.edgeDistancesToBipartite A |>.Nonempty := by
  dsimp only [edgeDistancesToBipartite, Set.nonempty_def]
  refine ⟨_, A.edgeSet, fun _ a ↦ a, ?_, rfl⟩
  use fun _ => 0
  simp

/-!
## Burling Graph Construction

We axiomatize the Burling graph structure. The key properties are:
1. Triangle-free
2. χ(B_k) = k
3. Recursive/hierarchical structure
-/

/--
Vertices of the k-th Burling graph.

CORRECTED definition:
- B_1 has a single vertex (base)
- B_{k+1} has vertices from B_k (embedded via `old`) plus new "frame" vertices
- The `new` constructor requires k ≥ 1 to ensure B_1 only has `base`
-/
inductive BurlingVertex : ℕ → Type
  | base : BurlingVertex 1
  | old {k : ℕ} (hk : k ≥ 1) : BurlingVertex k → BurlingVertex (k + 1)
  | new {k : ℕ} (hk : k ≥ 1) : ℕ → BurlingVertex (k + 1)

/-- Axiomatized adjacency for Burling graphs. -/
axiom BurlingGraphAdj : (k : ℕ) → BurlingVertex k → BurlingVertex k → Prop
axiom BurlingGraphAdj_symm : ∀ k u v, BurlingGraphAdj k u v → BurlingGraphAdj k v u
axiom BurlingGraphAdj_loopless : ∀ k v, ¬BurlingGraphAdj k v v

def BurlingGraph (k : ℕ) : SimpleGraph (BurlingVertex k) where
  Adj := BurlingGraphAdj k
  symm := BurlingGraphAdj_symm k
  loopless := BurlingGraphAdj_loopless k

/-!
## Key Properties of Burling Graphs (axiomatized from literature)
-/

/-- Burling graphs are triangle-free. (Known theorem from literature) -/
axiom burling_triangle_free (k : ℕ) : (BurlingGraph k).CliqueFree 3

/-- The k-th Burling graph has chromatic number exactly k. (Burling 1965) -/
axiom burling_chromatic_number (k : ℕ) (hk : k ≥ 1) :
    (BurlingGraph k).chromaticNumber = k

/-!
## The Core Mathematical Insight

For a graph G, let odd(G) = minimum number of edges to delete to make G bipartite.
Equivalently: odd(G) = |E(G)| - MaxCut(G)

A graph is bipartite iff it has no odd cycles.
So odd(G) = minimum edge hitting set for all odd cycles.

For Burling graphs:
- Triangle-free → minimum odd cycle length is 5
- Longer cycles share more edges (potentially)
- Question: Do 5-cycles in Burling graphs share edges efficiently?
-/

/-!
## Approach 1: Bound via odd cycle packing

If we can show that any n-vertex subgraph of B_k has at most √n edge-disjoint odd cycles,
then we need at most √n edge deletions (one per cycle).

Key lemma needed: In triangle-free graphs, odd cycles are "long" (≥5), so they
overlap more, limiting the number of edge-disjoint odd cycles.
-/

/--
In a graph with m edges where the shortest odd cycle has length ≥ 5,
the number of edge-disjoint odd cycles is at most m/5.

This is because each odd cycle uses at least 5 edges.
-/
theorem edge_disjoint_odd_cycles_bound_by_edges
    {W : Type*} (G : SimpleGraph W) [Fintype W] [DecidableRel G.Adj]
    (h_girth : G.CliqueFree 3) :
    True := by  -- Placeholder for the real statement
  trivial

/-!
## Approach 2: Use the recursive structure

B_1 has 1 vertex (trivially bipartite, needs 0 deletions)
B_{k+1} is built from B_k by adding new vertices

If we can show the bound propagates through the construction...
-/

/-- B_1 has exactly one vertex. -/
theorem burling_1_subsingleton : Subsingleton (BurlingVertex 1) := by
  constructor
  intro a b
  -- BurlingVertex 1 only has the `base` constructor
  -- `old` requires BurlingVertex 0 (which is empty) and `new` is for k+1 where k ≥ 1
  match a, b with
  | .base, .base => rfl

/-- A graph on a subsingleton type has no edges. -/
theorem SimpleGraph.edgeSet_empty_of_subsingleton
    {W : Type*} [Subsingleton W] (G : SimpleGraph W) :
    G.edgeSet = ∅ := by
  ext e
  simp only [Set.mem_empty_iff_false, iff_false]
  intro he
  rcases e with ⟨a, b⟩
  simp only [SimpleGraph.mem_edgeSet] at he
  have hab : a = b := Subsingleton.elim a b
  exact G.loopless a (hab ▸ he)

/-- B_1 has no edges (it's a single isolated vertex). -/
theorem burling_1_no_edges : (BurlingGraph 1).edgeSet = ∅ := by
  haveI : Subsingleton (BurlingVertex 1) := burling_1_subsingleton
  exact SimpleGraph.edgeSet_empty_of_subsingleton (BurlingGraph 1)

/-- B_1 is bipartite (trivially, since it has no edges). -/
theorem burling_1_bipartite_graph : IsBipartite (BurlingGraph 1) := by
  use fun _ => 0
  intro v w hvw
  exfalso
  have hempty : (BurlingGraph 1).edgeSet = ∅ := burling_1_no_edges
  have hedge : (BurlingGraph 1).Adj v w := hvw
  rw [SimpleGraph.edgeSet_eq_empty] at hempty
  exact hempty v w hedge

/-- B_1 is a single vertex, so it's bipartite (needs 0 edge deletions). -/
theorem burling_1_bipartite :
    ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph 1) n = 0 := by
  intro n
  -- B_1 has only one vertex (base), so any subgraph has at most 1 vertex
  -- A graph with ≤ 1 vertex has no edges, hence is bipartite
  -- Therefore maxSubgraphEdgeDistToBipartite = 0
  --
  -- The supremum of minEdgeDistToBipartite over all n-vertex subgraphs
  -- For n = 0: no such subgraphs exist, sSup ∅ = 0
  -- For n ≥ 1: the only subgraph has 1 vertex (base), which is bipartite with 0 deletions
  sorry

/-!
## Approach 3: Analyze the structure of odd cycles in Burling graphs

From the literature (arXiv:1703.07871), Burling graphs have a tree-decomposition
structure. Odd cycles must "cross" the tree structure in specific ways.

Hypothesis: The tree structure forces odd cycles to share edges at "bottleneck" points.
-/

/-!
## Working Towards the Main Theorem

We'll try to prove weaker bounds first and see if we can strengthen them.
-/

/-- Trivial bound: any n-vertex graph needs at most n(n-1)/2 deletions.
    This is proved in Problem074_experimental.lean as
    `SimpleGraph.maxSubgraphEdgeDistToBipartite_le_choose_two`. -/
theorem maxSubgraphEdgeDistToBipartite_le_edges
    {W : Type*} (G : SimpleGraph W) (n : ℕ) :
    SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ n.choose 2 := by
  unfold SimpleGraph.maxSubgraphEdgeDistToBipartite
  refine csSup_le' ?_
  intro m hm
  rcases hm with ⟨A, hn, hfin, rfl⟩
  -- minEdgeDistToBipartite A ≤ A.edgeSet.ncard ≤ n.choose 2
  -- (deleting all edges makes bipartite; n vertices have ≤ n.choose 2 edges)
  sorry

/--
For triangle-free graphs, a tighter bound should exist.

In a triangle-free graph on n vertices, the number of edges is at most n²/4 (Mantel's theorem).
But we want a bound on odd cycle hitting, not edge count.
-/
theorem triangle_free_edge_bound_mantel
    {W : Type*} (G : SimpleGraph W) [Fintype W] [DecidableRel G.Adj]
    (h : G.CliqueFree 3) :
    G.edgeFinset.card ≤ (Fintype.card W)^2 / 4 := by
  -- Mantel's theorem (1907)
  sorry

/-!
## The Main Conjecture

If we can prove this for Burling graphs, we win $500!
-/

/--
**THE $500 QUESTION FOR BURLING GRAPHS**

Conjecture: Every n-vertex subgraph of B_k can be made bipartite by deleting ≤ √n edges.
-/
def burling_sublinear_conjecture : Prop :=
  ∀ k : ℕ, ∀ n : ℕ,
    SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n

/-- The theorem we're trying to prove. -/
theorem burling_sublinear :
    ∀ k n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n := by
  intro k n
  -- Strategy:
  -- 1. Use triangle-free property to bound odd cycle structure
  -- 2. Use recursive/tree structure to show edge sharing
  -- 3. Conclude √n bound
  --
  -- Current status: OPEN - this is the $500 question!
  sorry

/-!
## If Burling Works: Constructing the Infinite Graph

If `burling_sublinear` holds, we can construct the prize-winning graph
as the disjoint union of all B_k.
-/

/-- Disjoint union of graphs (sigma type). -/
noncomputable def SimpleGraph.sigma' {ι : Type*} {W : ι → Type*} (G : ∀ i, SimpleGraph (W i)) :
    SimpleGraph (Sigma W) :=
  ⨆ i, (G i).map (Function.Embedding.sigmaMk i)

/--
If Burling graphs satisfy the √n bound, then their disjoint union has
infinite chromatic number and satisfies the same bound.
-/
theorem burling_infinite_graph_exists
    (h : ∀ k n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n) :
    ∃ (W : Type) (G : SimpleGraph W),
      G.chromaticNumber = ⊤ ∧
      ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n := by
  -- The disjoint union ⨆_k B_k has:
  -- 1. χ = ⊤ because χ(B_k) = k → ∞
  -- 2. The √n bound because finite subgraphs live in finitely many components
  sorry

/-!
## Research Status

### What we've established:
1. Burling graphs are triangle-free (axiom from literature)
2. χ(B_k) = k (axiom from literature)
3. Basic bounds (maxSubgraphEdgeDistToBipartite ≤ n.choose 2)

### What we need:
1. Deeper understanding of odd cycle structure in Burling graphs
2. Proof that the tree-decomposition forces edge sharing
3. The actual √n bound

### Next steps:
1. Read arXiv:1703.07871 for tree-decomposition details
2. Try to prove B_2 case explicitly (smallest non-trivial case)
3. Look for counterexamples (n-vertex subgraphs needing > √n deletions)
-/

end Erdos.Problem074.BurlingExperimental
