/-
Problem 74: Erdős Problem #74 - BURLING GRAPH APPROACH (For Aristotle API)

Status: EXPERIMENTAL
Prize: $500

This file uses Burling graphs as the candidate construction.
We've proved the k=0 and k=1 base cases. The k≥2 case is THE $500 QUESTION.

Burling graphs are:
- Triangle-free (no 3-cycles)
- Have unbounded chromatic number: χ(B_k) = k
- Intersection graphs of axis-aligned boxes in ℝ³
- The minimal hereditary class with unbounded χ (besides complete graphs)

KEY HYPOTHESIS: Being triangle-free might make Burling graphs "almost bipartite"
since only 5-cycles and longer can obstruct bipartiteness.
-/

import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card

open Filter SimpleGraph

namespace Erdos.Problem074.BurlingAristotle

universe u
variable {V : Type u}

/-! ## Core Definitions -/

def SimpleGraph.edgeDistancesToBipartite {G : SimpleGraph V} (A : G.Subgraph) : Set ℕ :=
  { (E.ncard) | (E : Set (Sym2 V)) (_ : E ⊆ A.edgeSet) (_ : IsBipartite (A.deleteEdges E).coe)}

noncomputable def SimpleGraph.minEdgeDistToBipartite {G : SimpleGraph V} (A : G.Subgraph) : ℕ :=
  sInf <| SimpleGraph.edgeDistancesToBipartite A

def SimpleGraph.subgraphEdgeDistsToBipartite (G : SimpleGraph V) (n : ℕ) : Set ℕ :=
  { (SimpleGraph.minEdgeDistToBipartite A) |
    (A : Subgraph G) (_ : A.verts.ncard = n) (_ : A.verts.Finite) }

noncomputable def SimpleGraph.maxSubgraphEdgeDistToBipartite
    (G : SimpleGraph V) (n : ℕ) : ℕ := sSup <| SimpleGraph.subgraphEdgeDistsToBipartite G n

/-! ## Helper Lemmas (PROVED) -/

theorem SimpleGraph.edgeDistancesToBipartite_nonempty {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.edgeDistancesToBipartite A |>.Nonempty := by
  dsimp only [edgeDistancesToBipartite, Set.nonempty_def]
  refine ⟨_, A.edgeSet, fun _ a ↦ a, ?_, rfl⟩
  use fun _ => 0
  simp

theorem SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite {G : SimpleGraph V}
    (A : G.Subgraph) (hA : IsBipartite A.coe) :
    SimpleGraph.minEdgeDistToBipartite A = 0 := by
  classical
  apply Nat.le_zero.1
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨(∅ : Set (Sym2 V)), by simp, ?_, by simp⟩
  have hcoe : (A.deleteEdges (∅ : Set (Sym2 V))).coe = A.coe := by ext v w; simp
  simpa [hcoe] using hA

/-! ## Burling Graph Construction -/

/-- Vertices of the k-th Burling graph.
    B_1 has a single vertex (base).
    B_{k+1} has vertices from B_k plus new frame vertices. -/
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

/-! ## Known Properties (AXIOMS from literature) -/

/-- Burling graphs are triangle-free. (Burling 1965) -/
axiom burling_triangle_free (k : ℕ) : (BurlingGraph k).CliqueFree 3

/-- The k-th Burling graph has chromatic number exactly k. (Burling 1965) -/
axiom burling_chromatic_number (k : ℕ) (hk : k ≥ 1) :
    (BurlingGraph k).chromaticNumber = k

/-! ## Base Cases (PROVED) -/

/-- B_1 has exactly one vertex. -/
theorem burling_1_subsingleton : Subsingleton (BurlingVertex 1) := by
  constructor
  intro a b
  match a, b with
  | .base, .base => rfl

/-- B_1 is bipartite (trivially, only one vertex). -/
theorem burling_1_bipartite_graph : IsBipartite (BurlingGraph 1) := by
  use fun _ => 0
  intro v w hvw
  exfalso
  haveI : Subsingleton (BurlingVertex 1) := burling_1_subsingleton
  have : v = w := Subsingleton.elim v w
  exact (BurlingGraph 1).loopless v (this ▸ hvw)

/-- For B_1, the √n bound holds (everything is 0). -/
theorem burling_1_bipartite :
    ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph 1) n = 0 := by
  intro n
  unfold SimpleGraph.maxSubgraphEdgeDistToBipartite
  apply le_antisymm
  · apply csSup_le'
    intro m hm
    rcases hm with ⟨A, hn, hfin, rfl⟩
    rw [SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite]
    use fun _ => 0
    intro v w hvw
    exfalso
    haveI : Subsingleton (BurlingVertex 1) := burling_1_subsingleton
    have : (v : BurlingVertex 1) = (w : BurlingVertex 1) := Subsingleton.elim v.val w.val
    have hadj : (BurlingGraph 1).Adj v.val w.val := A.adj_sub hvw
    exact (BurlingGraph 1).loopless v.val (this ▸ hadj)
  · exact Nat.zero_le _

/-! ## THE $500 QUESTION -/

/--
**THE $500 QUESTION: Prove this theorem!**

We need: ∀ k n, maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ √n

PROVED:
- k = 0: Empty graph, trivial
- k = 1: Single vertex (burling_1_bipartite)

OPEN:
- k ≥ 2: This is where the money is!

HINT FOR ARISTOTLE:
The key insight needed is something SPECIAL about Burling graphs beyond triangle-free.
Possible approaches:
1. Burling graphs might be sparse (O(n) edges in n-vertex subgraphs)
2. Odd cycles might share edges due to tree-decomposition structure
3. Box intersection geometry might constrain odd cycles
-/
theorem burling_sublinear :
    ∀ k n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ Nat.sqrt n := by
  intro k n
  match k with
  | 0 =>
    -- B_0 is empty (no constructors)
    simp only [SimpleGraph.maxSubgraphEdgeDistToBipartite]
    apply csSup_le'
    intro m hm
    rcases hm with ⟨A, hn, hfin, rfl⟩
    have hempty : IsEmpty (BurlingVertex 0) := ⟨fun v => by cases v⟩
    have hverts_empty : A.verts = ∅ := by
      ext x; simp only [Set.mem_empty_iff_false, iff_false]; exact fun _ => hempty.false x
    rw [hverts_empty, Set.ncard_empty] at hn
    subst hn
    apply Nat.le_zero.2
    apply SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite
    use fun _ => 0
    intro v _ _
    exfalso; exact hempty.false v.val
  | 1 =>
    -- B_1: single vertex
    have h := burling_1_bipartite n
    simp only [h]
    exact Nat.zero_le _
  | k + 2 =>
    -- THE $500 QUESTION: Prove this for k ≥ 2
    -- This requires insight into Burling graph structure beyond triangle-free
    sorry

end Erdos.Problem074.BurlingAristotle
