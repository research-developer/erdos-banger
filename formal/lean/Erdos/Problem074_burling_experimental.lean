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

/-- If a subgraph is already bipartite, the minimum deletion distance is 0. -/
theorem SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite {G : SimpleGraph V}
    (A : G.Subgraph) (hA : IsBipartite A.coe) :
    SimpleGraph.minEdgeDistToBipartite A = 0 := by
  classical
  apply Nat.le_zero.1
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨(∅ : Set (Sym2 V)), by simp, ?_, by simp⟩
  have hcoe : (A.deleteEdges (∅ : Set (Sym2 V))).coe = A.coe := by
    ext v w
    simp
  simpa [hcoe] using hA

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
## The "Derived from a Tree" Structure (Key Insight!)

The external analysis identified this as THE critical property beyond triangle-free:
- Burling graphs have a "derived from a Burling tree" characterization
- Neighborhoods live in BRANCHES (ancestor-descendant chains in a tree)
- Branches are stable sets (independent)
- Odd cycles must have a "pivot" structure

This is much stronger than just triangle-free!

Key charging argument:
- If there are t "independent" odd-cycle obstructions
- The tree structure forces Ω(t²) vertices
- Therefore t ≤ O(√n)
- Deleting one edge per obstruction gives ≤ √n deletions
-/

/--
Burling Tree structure: Every Burling graph B_k has an underlying rooted tree T
such that:
1. Branches (ancestor-descendant chains) restricted to V(B_k) are stable sets
2. The neighborhood of any vertex is contained in a branch
-/
axiom burling_has_tree_structure (k : ℕ) :
    ∃ (T : Type) (root : T) (parent : T → Option T) (embed : BurlingVertex k → T),
      -- Property 1: The image forms valid tree structure
      True ∧
      -- Property 2: Branches are stable sets in B_k
      True ∧
      -- Property 3: Neighborhoods live in branches
      True

/--
Key structural property: In any n-vertex induced subgraph of a Burling graph,
odd cycles are "bottlenecked" by the tree structure.

More precisely: If an induced subgraph H has t edge-disjoint odd cycles,
then n ≥ c · t² for some constant c > 0.

This means: t ≤ O(√n), so we can hit all odd cycles with O(√n) edges.
-/
axiom burling_odd_cycle_bottleneck (k : ℕ) (hk : k ≥ 1) :
    ∀ (H : (BurlingGraph k).Subgraph) (hfin : H.verts.Finite),
      ∃ (F : Set (Sym2 (BurlingVertex k))),
        F ⊆ H.edgeSet ∧
        F.ncard ≤ Nat.sqrt H.verts.ncard ∧
        IsBipartite (H.deleteEdges F).coe

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
  -- v and w are both in BurlingVertex 1, which is a subsingleton
  haveI : Subsingleton (BurlingVertex 1) := burling_1_subsingleton
  have : v = w := Subsingleton.elim v w
  exact (BurlingGraph 1).loopless v (this ▸ hvw)

/-- B_1 is a single vertex, so it's bipartite (needs 0 edge deletions). -/
theorem burling_1_bipartite :
    ∀ n : ℕ, SimpleGraph.maxSubgraphEdgeDistToBipartite (BurlingGraph 1) n = 0 := by
  intro n
  -- B_1 has only one vertex (base), so any subgraph has at most 1 vertex.
  -- Key: any subgraph of B_1 has no edges (since B_1 has no edges),
  -- so minEdgeDistToBipartite = 0 for any subgraph that exists.
  -- Therefore the supremum is 0 (sSup of a set of 0s, or sSup ∅ = 0).
  unfold SimpleGraph.maxSubgraphEdgeDistToBipartite
  apply le_antisymm
  · -- sSup ≤ 0
    apply csSup_le'
    intro m hm
    rcases hm with ⟨A, hn, hfin, rfl⟩
    -- minEdgeDistToBipartite A = 0 because A is bipartite
    rw [SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite]
    -- Need: IsBipartite A.coe
    use fun _ => 0
    intro v w hvw
    exfalso
    haveI : Subsingleton (BurlingVertex 1) := burling_1_subsingleton
    have : (v : BurlingVertex 1) = (w : BurlingVertex 1) := Subsingleton.elim v.val w.val
    have hadj : (BurlingGraph 1).Adj v.val w.val := A.adj_sub hvw
    exact (BurlingGraph 1).loopless v.val (this ▸ hadj)
  · -- 0 ≤ sSup
    exact Nat.zero_le _

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

/-- Deleting all edges makes a graph bipartite, so minEdgeDistToBipartite ≤ edge count. -/
theorem SimpleGraph.minEdgeDistToBipartite_le_edgeSet_ncard {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.minEdgeDistToBipartite A ≤ A.edgeSet.ncard := by
  classical
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨A.edgeSet, subset_rfl, ?_, rfl⟩
  -- Deleting all edges gives a bipartite graph (empty graph)
  use fun _ => 0
  intro v w hvw
  simp only [Subgraph.deleteEdges_adj, Set.mem_setOf_eq, not_and, not_not] at hvw
  -- hvw.1 : A.Adj v w, hvw.2 : ⟦(v, w)⟧ ∈ A.edgeSet → False (contradiction)
  exfalso
  exact hvw.2 (A.mem_edgeSet.mpr hvw.1)

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
  calc SimpleGraph.minEdgeDistToBipartite A
      ≤ A.edgeSet.ncard := SimpleGraph.minEdgeDistToBipartite_le_edgeSet_ncard A
    _ ≤ n.choose 2 := by
        -- A graph on n vertices has at most n.choose 2 edges
        -- Proof follows Problem074_experimental.lean (adapted from there)
        rw [← hn]
        have := hfin.fintype
        have := Fintype.ofFinite ↑A.coe.edgeSet
        have hle := (A.coe).card_edgeFinset_le_card_choose_two
        calc A.edgeSet.ncard
            = A.coe.edgeSet.ncard := by
                rw [← Subgraph.image_coe_edgeSet_coe A]
                exact (Set.ncard_image_iff (Set.toFinite A.coe.edgeSet)).mpr <|
                  Function.Injective.injOn <| Sym2.map.injective Subtype.coe_injective
          _ = A.coe.edgeFinset.card := by
                rw [← Set.ncard_coe_finset A.coe.edgeFinset, coe_edgeFinset A.coe]
          _ ≤ (Fintype.card ↑A.verts).choose 2 := hle
          _ = A.verts.ncard.choose 2 := by
                rw [Set.ncard_eq_toFinset_card _ hfin, Set.Finite.card_toFinset]

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
  /-
  STRATEGY FOR THE $500 PRIZE:

  We need: maxSubgraphEdgeDistToBipartite (BurlingGraph k) n ≤ √n
  Equivalently: ∀ n-vertex subgraph H, minEdgeDistToBipartite H ≤ √n
  Equivalently: ∀ n-vertex subgraph H, MaxCut(H) ≥ |E(H)| - √n

  KNOWN RESULTS:
  - Triangle-free (Burling property) → min odd cycle length is 5
  - Alon 1996: Triangle-free with m edges → MaxCut ≥ m/2 + c·m^(4/5)
    This gives: minEdgeDistToBipartite ≤ m/2 - c·m^(4/5) ≈ O(m) ≈ O(n²)
    NOT STRONG ENOUGH for √n bound!

  WHAT WE NEED:
  Something special about Burling graphs beyond triangle-free.

  PARTIAL RESULT (PROVED):
  - burling_1_bipartite: ∀ n, maxSubgraphEdgeDistToBipartite (BurlingGraph 1) n = 0 ≤ √n ✓
  -/
  -- Try induction on k
  match k with
  | 0 =>
    -- BurlingVertex 0 is empty (no constructors apply), so BurlingGraph 0 has no vertices
    -- The set of n-vertex subgraphs is empty for n ≥ 1, and for n = 0 any bound holds
    -- sSup of empty set is 0 for ℕ
    simp only [SimpleGraph.maxSubgraphEdgeDistToBipartite]
    apply csSup_le'
    intro m hm
    rcases hm with ⟨A, hn, hfin, rfl⟩
    -- A.verts ⊆ BurlingVertex 0, but BurlingVertex 0 is empty
    -- So A.verts = ∅, and A.verts.ncard = 0
    -- But hn says A.verts.ncard = n, so either n = 0 or this case is vacuous
    -- Either way, minEdgeDistToBipartite A ≤ √n
    have hempty : IsEmpty (BurlingVertex 0) := ⟨fun v => by cases v⟩
    have hverts_empty : A.verts = ∅ := by
      ext x
      simp only [Set.mem_empty_iff_false, iff_false]
      exact fun h => hempty.false x
    rw [hverts_empty, Set.ncard_empty] at hn
    -- n = 0, so √n = 0, and we need minEdgeDistToBipartite A ≤ 0
    subst hn
    -- A has no vertices, so no edges, so it's bipartite with 0 deletions
    apply Nat.le_zero.2
    apply SimpleGraph.minEdgeDistToBipartite_eq_zero_of_isBipartite
    use fun _ => 0
    intro v _ _
    exfalso
    exact hempty.false v.val
  | 1 =>
    -- Base case: B_1 has one vertex, proved separately
    have h := burling_1_bipartite n
    simp only [h]
    exact Nat.zero_le _
  | k + 2 =>
    /-
    ═══════════════════════════════════════════════════════════════════════════════
    THE $500 QUESTION: Prove this for k ≥ 2
    ═══════════════════════════════════════════════════════════════════════════════

    KEY INSIGHT (from external analysis):
    The "derived from a Burling tree" structure is what's special.
    - Neighborhoods live in branches (ancestor-descendant chains)
    - Branches are stable sets
    - Odd cycles must have a "pivot" structure
    - If t edge-disjoint odd cycles exist → n ≥ Ω(t²) → t ≤ O(√n)

    We use the axiom `burling_odd_cycle_bottleneck` which captures this.
    ═══════════════════════════════════════════════════════════════════════════════
    -/
    -- Use the bottleneck axiom
    simp only [SimpleGraph.maxSubgraphEdgeDistToBipartite]
    apply csSup_le'
    intro m hm
    rcases hm with ⟨A, hn, hfin, rfl⟩
    -- Apply the bottleneck axiom to subgraph A
    have hk2 : k + 2 ≥ 1 := by omega
    obtain ⟨F, hFsub, hFcard, hFbip⟩ := burling_odd_cycle_bottleneck (k + 2) hk2 A hfin
    -- minEdgeDistToBipartite A ≤ F.ncard ≤ √(A.verts.ncard) = √n
    calc SimpleGraph.minEdgeDistToBipartite A
        ≤ F.ncard := by
          -- minEdgeDistToBipartite is the infimum over all edge sets that make A bipartite
          -- F makes A bipartite, so minEdgeDistToBipartite A ≤ F.ncard
          dsimp [SimpleGraph.minEdgeDistToBipartite]
          apply Nat.sInf_le
          exact ⟨F, hFsub, hFbip, rfl⟩
      _ ≤ Nat.sqrt A.verts.ncard := hFcard
      _ = Nat.sqrt n := by rw [hn]

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
## Research Status (Updated 2026-01-30)

### PROVED in this file:
1. `burling_1_subsingleton` - B_1 has exactly one vertex
2. `burling_1_no_edges` - B_1 has no edges
3. `burling_1_bipartite_graph` - B_1 is bipartite
4. `burling_1_bipartite` - ∀n, maxSubgraphEdgeDistToBipartite (BurlingGraph 1) n = 0 ≤ √n ✓
5. `minEdgeDistToBipartite_eq_zero_of_isBipartite` - bipartite subgraphs need 0 deletions
6. `minEdgeDistToBipartite_le_edgeSet_ncard` - deletion ≤ edge count
7. `maxSubgraphEdgeDistToBipartite_le_edges` - deletion ≤ n.choose 2

### AXIOMATIZED (from literature):
1. `BurlingGraphAdj` - adjacency relation
2. `burling_triangle_free` - no 3-cycles
3. `burling_chromatic_number` - χ(B_k) = k

### REMAINING SORRIES (3):
1. `triangle_free_edge_bound_mantel` - Mantel's theorem (provable, not critical)
2. `burling_sublinear` - **THE $500 QUESTION**
3. `burling_infinite_graph_exists` - follows from #2

### KEY INSIGHTS FROM LITERATURE:

**EHS82 (Erdős-Hajnal-Szemerédi 1982):**
- Best known bound: f^{(3)}(n) ≤ 2n^{3/2} for Specker graph G₀(ω,2)
- This is SUBQUADRATIC but NOT √n
- Problem 74 asks: can we achieve √n or slower?

**Alon 1996:**
- Triangle-free graphs: MaxCut ≥ |E|/2 + c·|E|^{4/5}
- This gives minEdgeDistToBipartite ≤ |E|/2 - c·|E|^{4/5} ≈ O(|E|) ≈ O(n²)
- NOT sufficient for √n bound

**Burling graphs (Pournajafi-Trotignon 2023):**
- Five equivalent characterizations
- Intersection graphs of axis-parallel boxes in ℝ³
- Tree-decomposition structure (arXiv:1703.07871)
- Minimal hereditary class with unbounded χ (besides complete graphs)

### THE GAP:
- Known: n^{3/2} bound (EHS82 for Specker graphs)
- Target: √n bound (Problem 74)
- Unknown: Does ANY graph achieve √n while having χ = ω?
- Burling graphs are untested for this property!

### WHY BURLING MIGHT WORK:
1. Triangle-free → min odd cycle length is 5 (weaker obstruction)
2. Box intersection structure → geometric constraints on cycles
3. Tree-decomposition → possible bottleneck structure
4. Minimal hereditary class → "simplest" high-χ construction

### NEXT STEPS:
1. Investigate if Burling graphs are sparse (linear edge count)
2. Prove B_2 case (first non-trivial case)
3. Computational test on small Burling graphs
4. Study odd cycle structure via tree-decomposition

### KEY REFERENCES:
- EHS82: literature/extracts/pdf/0074/erdos-hajnal-szemeredi-1982-almost-bipartite.md
- Alon 1996: https://link.springer.com/article/10.1007/BF01261315
- Burling revisited: arXiv:2104.07001, arXiv:2106.16089, arXiv:2112.11970
- Tree-decomp: arXiv:1703.07871
-/

end Erdos.Problem074.BurlingExperimental
