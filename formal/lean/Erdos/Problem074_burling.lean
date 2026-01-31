/-
Problem 74: Erdős Problem #74 - BURLING GRAPH APPROACH

Status: EXPERIMENTAL
Prize: $500

This file attempts to solve Problem 74 using Burling graphs as the candidate construction.

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
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Finset.Powerset

open Filter SimpleGraph
open scoped BigOperators

namespace Erdos.Problem074.Burling

/-!
## Core Definitions (copied from Problem074_experimental.lean)
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
## Burling Graph Construction

The Burling sequence B_1, B_2, B_3, ... is defined recursively.

From the literature, there are several equivalent definitions:
1. Intersection graphs of axis-aligned boxes in ℝ³ (original Burling 1965)
2. "Graphs derived from a tree" (Pournajafi-Trotignon 2024)
3. Recursive frame construction (arXiv:1703.07871)

We use a simplified vertex type based on the recursive structure.
-/

/--
Vertices of the k-th Burling graph.
These represent "frames" in the box intersection model.

For B_1: single vertex (the base case)
For B_{k+1}: vertices of B_k plus new "frame" vertices
-/
inductive BurlingVertex : ℕ → Type
  | base : BurlingVertex 1
  | old {k : ℕ} : BurlingVertex k → BurlingVertex (k + 1)
  | new {k : ℕ} : ℕ → BurlingVertex (k + 1)

/--
The k-th Burling graph.

Edges connect vertices based on the recursive frame containment structure.
This is a simplified placeholder - the exact edge relation needs to match the literature.

NOTE: We define this non-recursively using an axiom to avoid termination issues.
The real definition would require a more careful inductive construction.
-/
axiom BurlingGraphAdj : (k : ℕ) → BurlingVertex k → BurlingVertex k → Prop
axiom BurlingGraphAdj_symm : ∀ k u v, BurlingGraphAdj k u v → BurlingGraphAdj k v u
axiom BurlingGraphAdj_loopless : ∀ k v, ¬BurlingGraphAdj k v v

def BurlingGraph (k : ℕ) : SimpleGraph (BurlingVertex k) where
  Adj := BurlingGraphAdj k
  symm := BurlingGraphAdj_symm k
  loopless := BurlingGraphAdj_loopless k

/-!
## Key Properties of Burling Graphs

These are the properties we need to prove (or axiomatize).
-/

/--
Burling graphs are triangle-free.
This is a known theorem from the literature.
-/
axiom burling_triangle_free (k : ℕ) : (BurlingGraph k).CliqueFree 3

/--
The k-th Burling graph has chromatic number exactly k.
This is Burling's main theorem (1965).
-/
axiom burling_chromatic_number (k : ℕ) (hk : k ≥ 1) :
    (BurlingGraph k).chromaticNumber = k

/-!
## The Prize Question

If we can prove this theorem, we win $500!
-/

/--
**THE $500 QUESTION**

Conjecture: Burling graphs satisfy a sublinear edge-deletion bound.

Since Burling graphs are triangle-free, the only odd cycles are 5-cycles, 7-cycles, etc.
These longer cycles might "share edges" in a way that allows sublinear deletion.
-/
def burling_sublinear_conjecture : Prop :=
  ∀ k : ℕ, ∀ n : ℕ,
    SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n

/--
Stronger version: the infinite disjoint union of all Burling graphs satisfies the bound.
-/
def burling_infinite_satisfies_sqrt : Prop :=
  ∃ (W : Type) (G : SimpleGraph W),
    G.chromaticNumber = ⊤ ∧
    ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n

/-!
## Attempting the Proof

Strategy:
1. For any n-vertex induced subgraph of B_k, bound the number of odd cycles
2. Show that odd cycles in Burling graphs share edges efficiently
3. Conclude that √n edge deletions suffice

The key insight should come from the recursive/hierarchical structure.
-/

-- Helper: count edges in odd cycles
-- TODO: Define odd cycle structure and edge sharing

-- Attempt at the main theorem
theorem burling_sublinear_attempt :
    ∀ k n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n := by
  intro k n
  -- This is where the magic needs to happen
  -- We need to show that:
  -- 1. Take any n-vertex induced subgraph H of B_k
  -- 2. H has at most √n edge-disjoint odd cycles (because triangle-free + structure)
  -- 3. Therefore deleting √n edges can hit all odd cycles
  sorry

/-!
## Research Notes

### What we know:
- B_k is triangle-free, so min odd cycle length is 5
- B_k has chromatic number k (so definitely has odd cycles for k ≥ 3)
- B_k has a recursive/hierarchical structure from box intersections

### What we need to prove:
- In any n-vertex subgraph, odd cycles share edges efficiently
- Specifically: at most √n edge deletions suffice to break all odd cycles

### Potential approaches:
1. **Structural**: Use the tree-decomposition from arXiv:1703.07871
2. **Counting**: Bound number of edge-disjoint odd cycles
3. **Induction**: Use the recursive B_k → B_{k+1} construction

### If this fails:
- Compute the actual growth rate of maxSubgraphEdgeDistToBipartite for small B_k
- If it's linear (like Kneser), Burling isn't the answer
- Move to next candidate (shift graphs?)
-/

end Erdos.Problem074.Burling
