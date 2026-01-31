/-
Problem 74: Erdős Problem #74

Status: open
Prize: $500
Tags: graph theory, chromatic number, bipartite

Statement:
Let $f(n)\to \infty$ (possibly very slowly). Is there a graph of infinite chromatic
number such that every finite subgraph on $n$ vertices can be made bipartite by
deleting at most $f(n)$ edges?

Reference: https://www.erdosproblems.com/74

Upstream source: formal/lean/Upstream/FormalConjectures/ErdosProblems/74.lean
-/

import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Subgraph
import Mathlib.Combinatorics.SimpleGraph.Coloring
import Mathlib.Combinatorics.SimpleGraph.Bipartite
import Mathlib.Data.Set.Finite.Basic
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Order.Filter.AtTopBot.Basic
import Mathlib.Data.Nat.Sqrt
import Mathlib.Data.Real.Basic
import Mathlib.Data.Set.Card
import Mathlib.Data.Set.Card.Arithmetic

open Filter SimpleGraph
open scoped BigOperators

namespace Erdos.Problem074

universe u
variable {V : Type u}

/-!
## Key Definitions

These definitions capture the mathematical structure of Problem 74.
Adapted from the formal-conjectures upstream project.
-/

/--
For a given subgraph `A`, this is the set of all numbers `k` such that `A` can be made
bipartite by deleting `k` edges.
-/
def SimpleGraph.edgeDistancesToBipartite {G : SimpleGraph V} (A : G.Subgraph) : Set ℕ :=
  { (E.ncard) | (E : Set (Sym2 V)) (_ : E ⊆ A.edgeSet) (_ : IsBipartite (A.deleteEdges E).coe)}

/--
The minimum number of edges that must be deleted from a subgraph `A` to make it bipartite.
-/
noncomputable def SimpleGraph.minEdgeDistToBipartite {G : SimpleGraph V} (A : G.Subgraph) : ℕ :=
  sInf <| SimpleGraph.edgeDistancesToBipartite A

/--
For a graph `G` and a number `n`, this is the set of `minEdgeDistToBipartite A` for all
induced subgraphs `A` of `G` on `n` vertices.
-/
def SimpleGraph.subgraphEdgeDistsToBipartite (G : SimpleGraph V) (n : ℕ) : Set ℕ :=
  { (SimpleGraph.minEdgeDistToBipartite A) |
    (A : Subgraph G) (_ : A.verts.ncard = n) (_ : A.verts.Finite) }

/--
For a given graph $G$ and size $n$, this defines the smallest number $k$
such that any subgraph of $G$ on $n$ vertices can be made bipartite by deleting
at most $k$ edges.

This value is optimal because it is the maximum of `minEdgeDistToBipartite` taken
over all $n$-vertex subgraphs. This means there exists at least one $n$-vertex
subgraph that requires exactly this many edge deletions.

This is Definition 3.1 in [EHS82].

[EHS82] Erdős, P. and Hajnal, A. and Szemerédi, E.,
  *On almost bipartite large chromatic graphs* Theory and practice of combinatorics (1982), 117-123.
-/
noncomputable def SimpleGraph.maxSubgraphEdgeDistToBipartite
    (G : SimpleGraph V) (n : ℕ) : ℕ := sSup <| SimpleGraph.subgraphEdgeDistsToBipartite G n

/-!
## Supporting Lemmas (PROVED in upstream)

These lemmas establish basic properties needed for the main theorem.
-/

/--
The set of edge distances to a bipartite graph is always non-empty because deleting all edges
from a graph makes it bipartite.
-/
theorem SimpleGraph.edgeDistancesToBipartite_nonempty {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.edgeDistancesToBipartite A |>.Nonempty := by
  dsimp only [edgeDistancesToBipartite, Set.nonempty_def]
  refine ⟨_, A.edgeSet, fun _ a ↦ a, ?_, rfl⟩
  use fun _ => 0
  simp

/--
The set of minimum edge distances to bipartite for subgraphs of size `n` is bounded above.
A graph on `n` vertices has at most `n choose 2` edges, and deleting all of them
makes the graph bipartite, providing a straightforward upper bound.
-/
theorem SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G : SimpleGraph V) (n : ℕ) :
    ∀ m ∈ SimpleGraph.subgraphEdgeDistsToBipartite G n, m ≤ n.choose 2 := by
  intro m h
  replace ⟨A, ⟨hn, h_fin, h⟩⟩ := h
  rw [← h]
  have : A.edgeSet.ncard ≤ n.choose 2 := by
    rw [← hn]
    have := h_fin.fintype
    have := Fintype.ofFinite ↑A.coe.edgeSet
    convert (A.coe).card_edgeFinset_le_card_choose_two
    · rw [← Set.ncard_coe_finset A.coe.edgeFinset, coe_edgeFinset A.coe,
        ← Subgraph.image_coe_edgeSet_coe A]
      exact (Set.ncard_image_iff (Set.toFinite A.coe.edgeSet)).mpr <|
        Function.Injective.injOn <| Sym2.map.injective Subtype.coe_injective
    · rw [Set.ncard_eq_toFinset_card _ h_fin, Set.Finite.card_toFinset]
  refine le_trans ?_ this
  apply Nat.sInf_le
  -- `A.edgeSet.ncard` is in the set of achievable deletion counts, by deleting all edges.
  simp [SimpleGraph.edgeDistancesToBipartite]
  refine ⟨A.edgeSet, ?_, subset_rfl, rfl⟩
  use fun _ => 0
  simp

theorem SimpleGraph.subgraphEdgeDistsToBipartite_bddAbove (G : SimpleGraph V) (n : ℕ) :
    BddAbove (SimpleGraph.subgraphEdgeDistsToBipartite G n) := by
  use n.choose 2
  simp only [upperBounds, Set.mem_setOf_eq]
  intro m hm
  exact SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G := G) n m hm

/-!
## Additional Derived Facts

These are small, self-contained facts about the definitions above. They are useful for:
- sanity checks (the quantities are always finite),
- extracting explicit witnesses (a *minimum* number of edge deletions is attained),
- relating variants of the conjecture.
-/

/-- `minEdgeDistToBipartite` is attained: there is a deletion set achieving the minimum. -/
theorem SimpleGraph.minEdgeDistToBipartite_mem_edgeDistancesToBipartite {G : SimpleGraph V}
    (A : G.Subgraph) :
    SimpleGraph.minEdgeDistToBipartite A ∈ SimpleGraph.edgeDistancesToBipartite A := by
  classical
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  exact Nat.sInf_mem (SimpleGraph.edgeDistancesToBipartite_nonempty (A := A))

/-- Witness form of `minEdgeDistToBipartite_mem_edgeDistancesToBipartite`. -/
theorem SimpleGraph.exists_deleteEdges_bipartite_minEdgeDist {G : SimpleGraph V} (A : G.Subgraph) :
    ∃ (E : Set (Sym2 V)), E ⊆ A.edgeSet ∧ IsBipartite (A.deleteEdges E).coe ∧
      E.ncard = SimpleGraph.minEdgeDistToBipartite A := by
  classical
  rcases (by
    simpa [SimpleGraph.edgeDistancesToBipartite] using
      (SimpleGraph.minEdgeDistToBipartite_mem_edgeDistancesToBipartite (A := A))) with
    ⟨E, hBip, hSub, hCard⟩
  exact ⟨E, hSub, hBip, hCard⟩

/-- Trivial upper bound: deleting all edges makes a graph bipartite. -/
theorem SimpleGraph.minEdgeDistToBipartite_le_edgeSet_ncard {G : SimpleGraph V} (A : G.Subgraph) :
    SimpleGraph.minEdgeDistToBipartite A ≤ A.edgeSet.ncard := by
  classical
  dsimp [SimpleGraph.minEdgeDistToBipartite]
  apply Nat.sInf_le
  refine ⟨A.edgeSet, subset_rfl, ?_, rfl⟩
  refine ⟨fun _ => 0, ?_⟩
  simp

/-- If a subgraph is already bipartite, the minimum deletion distance is `0`. -/
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

/-- Uniform finiteness bound: any `n`-vertex graph has at most `n.choose 2` edges. -/
theorem SimpleGraph.maxSubgraphEdgeDistToBipartite_le_choose_two (G : SimpleGraph V) (n : ℕ) :
    SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ n.choose 2 := by
  dsimp [SimpleGraph.maxSubgraphEdgeDistToBipartite]
  refine csSup_le' (a := n.choose 2) (s := SimpleGraph.subgraphEdgeDistsToBipartite G n) ?_
  intro m hm
  exact SimpleGraph.subgraphEdgeDistsToBipartite_le_choose_two (G := G) n m hm

/-!
## Main Conjectures (OPEN)

Problem 74 is open (as of 2026). We record its statement as a `Prop` (rather than a `theorem`
with `sorry`) so this file remains warning-free and the goalposts stay honest.
-/

/--
**Main Conjecture (Problem 74)**.

Let `f(n) → ∞` (possibly very slowly).
Is there a graph of infinite chromatic number such that every finite subgraph on `n` vertices
can be made bipartite by deleting at most `f(n)` edges?
-/
def erdos_74 : Prop :=
  ∀ f : ℕ → ℕ, Tendsto f atTop atTop →
    (∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
      ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ f n)

/--
**Known positive result (linear bound).**

There exist graphs of infinite chromatic number such that every finite `n`-vertex subgraph
can be made bipartite by deleting at most `ε * n` edges (for any fixed `ε > 0`).

This is proved in the finite setting by Rödl (1982) (and independently by Lovász), in the form of
existence of finite graphs with the `(ε, k)`-*edge* property. Taking a disjoint union over `k → ∞`
produces a graph with `chromaticNumber = ⊤` and the same linear edge-deletion-to-bipartite bound.

We record this as a statement here; formalizing Rödl's construction and the disjoint-union argument
is future work.
-/
def erdos_74_linear : Prop :=
  ∀ ε : ℝ, 0 < ε →
    ∃ (W : Type*) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
      ∀ n : ℕ, (SimpleGraph.maxSubgraphEdgeDistToBipartite G n : ℝ) ≤ ε * (n : ℝ)

/--
**Variant: Square Root Bound**.

Is there a graph of infinite chromatic number such that every finite subgraph on `n` vertices
can be made bipartite by deleting at most `√n` edges?

This remains open even though `Nat.sqrt n → ∞`.
-/
def erdos_74_sqrt : Prop :=
  ∃ (W : Type u) (G : SimpleGraph W), G.chromaticNumber = ⊤ ∧
    ∀ n, SimpleGraph.maxSubgraphEdgeDistToBipartite G n ≤ Nat.sqrt n

/-!
## Proof of the Linear Case (Rödl 1982)

Rödl (1982) (and independently Lovász) proved the finite `(ε, k)`-*edge property*:
for any `ε > 0` and `k : ℕ` there exists a graph with chromatic number at least `k` such that every
finite `n`-vertex subgraph can be made bipartite by deleting at most `ε * n` edges.

Taking a disjoint union over `k → ∞` yields a graph with `chromaticNumber = ⊤` that satisfies the
same linear edge-deletion bound. We formalize this disjoint-union argument and *axiomatize* the
finite Rödl/Lovász construction.
-/

/-- Axiomatized Rödl/Lovász finite theorem: graphs with the `(ε, k)`-edge property exist. -/
axiom rodl_modified_kneser_exists :
    ∀ ε : ℝ, 0 < ε → ∀ k : ℕ,
      ∃ (W : Type u) (G : SimpleGraph W),
        k ≤ G.chromaticNumber ∧
        ∀ n : ℕ, (SimpleGraph.maxSubgraphEdgeDistToBipartite G n : ℝ) ≤ ε * (n : ℝ)

/-- The disjoint union (sigma-type union) of a family of graphs. -/
noncomputable def SimpleGraph.sigma {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i)) :
    SimpleGraph (Sigma W) :=
  ⨆ i, (G i).map (Function.Embedding.sigmaMk i)

theorem SimpleGraph.sigma_adj_iff {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i))
    (x y : Sigma W) :
    (SimpleGraph.sigma (G := G)).Adj x y ↔
      ∃ i, ∃ u v : W i, (G i).Adj u v ∧ Sigma.mk i u = x ∧ Sigma.mk i v = y := by
  classical
  simp [SimpleGraph.sigma, SimpleGraph.map_adj]

theorem SimpleGraph.sigma_adj_mk_mk {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i))
    (i : ι) (u v : W i) :
    (SimpleGraph.sigma (G := G)).Adj (Sigma.mk i u) (Sigma.mk i v) ↔ (G i).Adj u v := by
  classical
  constructor
  · intro h
    rcases (SimpleGraph.sigma_adj_iff (G := G) (x := Sigma.mk i u) (y := Sigma.mk i v)).1 h with
      ⟨j, u', v', hadj, hu, hv⟩
    have hij : j = i := (Sigma.mk.inj hu).1
    subst hij
    have hu' : u' = u := eq_of_heq (Sigma.mk.inj hu).2
    have hv' : v' = v := eq_of_heq (Sigma.mk.inj hv).2
    simpa [hu', hv'] using hadj
  · intro h
    exact
      (SimpleGraph.sigma_adj_iff (G := G) (x := Sigma.mk i u) (y := Sigma.mk i v)).2
        ⟨i, u, v, h, rfl, rfl⟩

theorem SimpleGraph.sigma_adj_mk_mk_of_ne {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i))
    {i j : ι} (hij : i ≠ j) (u : W i) (v : W j) :
    ¬(SimpleGraph.sigma (G := G)).Adj (Sigma.mk i u) (Sigma.mk j v) := by
  intro h
  rcases (SimpleGraph.sigma_adj_iff (G := G) (x := Sigma.mk i u) (y := Sigma.mk j v)).1 h with
    ⟨k, u', v', -, hu, hv⟩
  have hk : k = i := (Sigma.mk.inj hu).1
  subst hk
  exact hij ((Sigma.mk.inj hv).1)

/-- The canonical homomorphism embedding a component into the disjoint union. -/
noncomputable def SimpleGraph.sigmaHom {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i))
    (i : ι) : (G i) →g SimpleGraph.sigma (G := G) where
  toFun := Sigma.mk i
  map_rel' {u v} huv := by
    exact (SimpleGraph.sigma_adj_mk_mk (G := G) i u v).2 huv

theorem SimpleGraph.chromaticNumber_sigma_eq_top_of_unbounded
    {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i))
    (hχ : ∀ n : ℕ, ∃ i, (n + 1 : ℕ∞) ≤ (G i).chromaticNumber) :
    (SimpleGraph.sigma (G := G)).chromaticNumber = ⊤ := by
  classical
  -- It suffices to show there is no finite coloring.
  by_contra hne
  rcases (SimpleGraph.chromaticNumber_ne_top_iff_exists (G := SimpleGraph.sigma (G := G))).1 hne with
    ⟨n, hn⟩
  rcases hχ n with ⟨i, hi⟩
  have hGi : (G i).Colorable n :=
    SimpleGraph.Colorable.of_hom (SimpleGraph.sigmaHom (G := G) i) hn
  have : (n + 1 : ℕ∞) ≤ (n : ℕ∞) := by
    calc
      (n + 1 : ℕ∞) ≤ (G i).chromaticNumber := hi
      _ ≤ (n : ℕ∞) := by
        -- `n`-colorability bounds the chromatic number by `n`.
        exact (SimpleGraph.Colorable.chromaticNumber_le hGi)
  have hnat : n.succ ≤ n := by
    have : (↑(n + 1) : ℕ∞) ≤ (n : ℕ∞) := by
      simpa [Nat.cast_add, Nat.cast_one] using this
    exact (Nat.cast_le.mp this)
  exact (Nat.not_succ_le_self n) hnat

/--
Technical lemma: the linear `ε * n` bound on `maxSubgraphEdgeDistToBipartite` is preserved by the
sigma-type disjoint union construction.

This is a straightforward combinatorial argument (split a finite subgraph across components and
union the edge-deletion witnesses).
-/
theorem SimpleGraph.maxSubgraphEdgeDistToBipartite_sigma_le_linear
    {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i)) (ε : ℝ) (hε : 0 ≤ ε)
    (h : ∀ i : ι, ∀ n : ℕ,
      (SimpleGraph.maxSubgraphEdgeDistToBipartite (G i) n : ℝ) ≤ ε * (n : ℝ)) :
    ∀ n : ℕ,
      (SimpleGraph.maxSubgraphEdgeDistToBipartite (SimpleGraph.sigma (G := G)) n : ℝ) ≤
        ε * (n : ℝ) := by
  classical
  intro n
  -- Let `S` be the set of achievable deletion distances for `n`-vertex subgraphs.
  let S : Set ℕ := SimpleGraph.subgraphEdgeDistsToBipartite (SimpleGraph.sigma (G := G)) n
  by_cases hS : S.Nonempty
  ·
    have hBdd : BddAbove S :=
      SimpleGraph.subgraphEdgeDistsToBipartite_bddAbove (G := SimpleGraph.sigma (G := G)) (n := n)

    -- In `ℕ`, a bounded nonempty set has its `sSup` as an element of the set.
    have hmem :
        SimpleGraph.maxSubgraphEdgeDistToBipartite (SimpleGraph.sigma (G := G)) n ∈ S := by
      dsimp [SimpleGraph.maxSubgraphEdgeDistToBipartite, S]
      exact Nat.sSup_mem hS hBdd

    -- Extract a witness `A` achieving the maximum value.
    rcases (by
      simpa [S, SimpleGraph.subgraphEdgeDistsToBipartite] using hmem) with
      ⟨A, hA_finite, hnA, hEq⟩

    -- Core bound: the chosen `A` can be made bipartite by deleting at most `ε * n` edges.
    have hA_bound :
        ((SimpleGraph.minEdgeDistToBipartite A : ℕ) : ℝ) ≤ ε * (n : ℝ) := by
      -- Split `A` across components.
      let Iset : Set ι := Sigma.fst '' A.verts
      have hIset_finite : Iset.Finite := hA_finite.image Sigma.fst
      let I : Finset ι := hIset_finite.toFinset

      let Ai : ∀ i : ι, (G i).Subgraph :=
        fun i => Subgraph.comap (SimpleGraph.sigmaHom (G := G) i) A

      have hAi_finite : ∀ i : ι, (Ai i).verts.Finite := by
        intro i
        -- `Ai i.verts = (Sigma.mk i) ⁻¹' A.verts` and `Sigma.mk i` is an embedding.
        simpa [Ai] using
          (Set.Finite.preimage_embedding (Function.Embedding.sigmaMk i) hA_finite)

      -- Choose minimal deletion witnesses for each component.
      choose Edel hEdel_sub hEdel_bip hEdel_card using
        fun i : ι => SimpleGraph.exists_deleteEdges_bipartite_minEdgeDist (A := Ai i)

      -- Combine deletions across the finitely many relevant components.
      let E : Set (Sym2 (Sigma W)) := ⋃ i ∈ I, Sym2.map (Sigma.mk i) '' Edel i

      have hE_subset : E ⊆ A.edgeSet := by
        intro e he
        rcases (by simpa [E] using he) with ⟨i, _hiI, e0, he0, rfl⟩
        have he0' : e0 ∈ (Ai i).edgeSet := hEdel_sub i he0
        induction e0 using Sym2.ind with
        | h u v =>
          have hAdj : A.Adj (Sigma.mk i u) (Sigma.mk i v) := by
            have : (Ai i).Adj u v := (Subgraph.mem_edgeSet).1 he0'
            simpa [Ai] using this.2
          exact (Subgraph.mem_edgeSet).2 hAdj

      have hA_delete_bip : IsBipartite (A.deleteEdges E).coe := by
        refine ⟨Coloring.mk (fun x : (A.deleteEdges E).verts => ?_) ?_⟩
        · -- Color each vertex using the bipartite coloring of its component.
          let i : ι := x.1.1
          let u : W i := x.1.2
          have hx : Sigma.mk i u = x.1 := by rfl
          have hu : u ∈ (Ai i).verts := by
            -- `u ∈ (Ai i).verts` means `Sigma.mk i u ∈ A.verts`.
            -- This follows from `x.2 : x.1 ∈ A.verts` since `Sigma.mk i u = x.1`.
            have : Sigma.mk i u ∈ A.verts := by simpa [hx] using x.2
            simpa [Ai] using this
          exact (hEdel_bip i).some ⟨u, hu⟩
        · intro x y hxy
          have hxy' : A.Adj x y ∧ s(x.1, y.1) ∉ E := by
            simpa using (Subgraph.deleteEdges_adj (G' := A) (s := E) x y).1 hxy
          have hAxy : A.Adj x y := hxy'.1
          have hnotE : s(x.1, y.1) ∉ E := hxy'.2

          -- Adjacent vertices lie in the same component.
          let i : ι := x.1.1
          let j : ι := y.1.1
          have hij : i = j := by
            by_contra hne
            have : ¬(SimpleGraph.sigma (G := G)).Adj (Sigma.mk i x.1.2) (Sigma.mk j y.1.2) :=
              SimpleGraph.sigma_adj_mk_mk_of_ne (G := G) hne x.1.2 y.1.2
            exact this (A.adj_sub hAxy)
          -- Rewrite to a single component `i`.
          have hij' : j = i := hij.symm
          subst j
          let u : W i := x.1.2
          let v : W i := y.1.2

          have hu : u ∈ (Ai i).verts := by
            have hx : Sigma.mk i u = x.1 := by rfl
            have : Sigma.mk i u ∈ A.verts := by simpa [hx] using x.2
            simpa [Ai] using this
          have hv : v ∈ (Ai i).verts := by
            have hy : Sigma.mk i v = y.1 := by rfl
            have : Sigma.mk i v ∈ A.verts := by simpa [hy] using y.2
            simpa [Ai] using this

          have hGiAdj : (G i).Adj u v := by
            have hSigma : (SimpleGraph.sigma (G := G)).Adj (Sigma.mk i u) (Sigma.mk i v) :=
              A.adj_sub hAxy
            exact (SimpleGraph.sigma_adj_mk_mk (G := G) i u v).1 hSigma

          have hAiAdj : (Ai i).Adj u v := by
            simpa [Ai, hGiAdj] using And.intro hGiAdj hAxy

          have hnotEdel : s(u, v) ∉ Edel i := by
            intro hmem
            apply hnotE
            have hiIset : i ∈ Iset := ⟨x.1, x.2, rfl⟩
            have hiI : i ∈ I := by simpa [I, Iset] using hiIset
            have : Sym2.map (Sigma.mk i) (s(u, v)) ∈ E := by
              simp [E, hiI, hmem]
            simpa [Sym2.map_pair_eq] using this

          have hCompAdj : ((Ai i).deleteEdges (Edel i)).Adj u v := by
            have : (Ai i).Adj u v ∧ s(u, v) ∉ Edel i := ⟨hAiAdj, hnotEdel⟩
            simpa using (Subgraph.deleteEdges_adj (G' := Ai i) (s := Edel i) u v).2 this

          -- Apply the component coloring validity.
          have hu' : u ∈ ((Ai i).deleteEdges (Edel i)).verts := by simpa using hu
          have hv' : v ∈ ((Ai i).deleteEdges (Edel i)).verts := by simpa using hv
          have hCompAdj' :
              ((Ai i).deleteEdges (Edel i)).coe.Adj ⟨u, hu'⟩ ⟨v, hv'⟩ :=
            Subgraph.Adj.coe hCompAdj
          have hcol :=
            (hEdel_bip i).some.valid hCompAdj'
          simpa using hcol

      -- `E` is a deletion witness, so `minEdgeDistToBipartite A ≤ |E|`.
      have hMin_le_E : SimpleGraph.minEdgeDistToBipartite A ≤ E.ncard := by
        classical
        dsimp [SimpleGraph.minEdgeDistToBipartite]
        refine Nat.sInf_le ?_
        exact ⟨E, hE_subset, hA_delete_bip, rfl⟩

      -- Bound `|E|` by the sum of component deletion sizes.
      have hE_ncard_le_sum :
          E.ncard ≤ ∑ i ∈ I, (Edel i).ncard := by
        have hE' :
            (⋃ i ∈ I, Sym2.map (Sigma.mk i) '' Edel i).ncard ≤
              ∑ i ∈ I, (Sym2.map (Sigma.mk i) '' Edel i).ncard :=
          Finset.set_ncard_biUnion_le I (fun i => Sym2.map (Sigma.mk i) '' Edel i)
        have hinj : ∀ i : ι, Function.Injective (Sym2.map (Sigma.mk i)) := fun i =>
          Sym2.map.injective (fun _ _ hab => eq_of_heq (Sigma.mk.inj hab).2)
        simpa [E, Set.ncard_image_of_injective, hinj] using hE'

      -- Each component deletion size is bounded linearly in its component vertex count.
      have hEdel_le :
          ∀ i ∈ I, ((Edel i).ncard : ℝ) ≤ ε * ((Ai i).verts.ncard : ℝ) := by
        intro i _hiI
        have hMin_le_max :
            SimpleGraph.minEdgeDistToBipartite (Ai i) ≤
              SimpleGraph.maxSubgraphEdgeDistToBipartite (G i) (Ai i).verts.ncard := by
          have hmem' :
              SimpleGraph.minEdgeDistToBipartite (Ai i) ∈
                SimpleGraph.subgraphEdgeDistsToBipartite (G i) (Ai i).verts.ncard := by
            exact ⟨Ai i, rfl, hAi_finite i, rfl⟩
          have hbdd' :
              BddAbove (SimpleGraph.subgraphEdgeDistsToBipartite (G i) (Ai i).verts.ncard) :=
            SimpleGraph.subgraphEdgeDistsToBipartite_bddAbove (G := G i) (n := (Ai i).verts.ncard)
          simpa [SimpleGraph.maxSubgraphEdgeDistToBipartite] using le_csSup hbdd' hmem'

        have hcast :
            ((SimpleGraph.minEdgeDistToBipartite (Ai i) : ℕ) : ℝ) ≤
              (SimpleGraph.maxSubgraphEdgeDistToBipartite (G i) (Ai i).verts.ncard : ℝ) := by
          exact_mod_cast hMin_le_max

        have hlin_i :
            (SimpleGraph.maxSubgraphEdgeDistToBipartite (G i) (Ai i).verts.ncard : ℝ) ≤
              ε * ((Ai i).verts.ncard : ℝ) := by
          simpa using h i (Ai i).verts.ncard

        simpa [hEdel_card i] using hcast.trans hlin_i

      -- Relate the sum of component vertex counts to `n`.
      have hVerts_sum :
          (∑ i ∈ I, (Ai i).verts.ncard) = n := by
        let Vset : ι → Set (Sigma W) := fun i => Sigma.mk i '' (Ai i).verts
        have hVset_finite : ∀ i ∈ Iset, (Vset i).Finite := by
          intro i _hi
          exact (hAi_finite i).image (Sigma.mk i)
        have hVset_disjoint : Iset.PairwiseDisjoint Vset := by
          intro i _hi j _hj hij
          refine Set.disjoint_left.2 ?_
          intro x hx_i hx_j
          rcases hx_i with ⟨u, _hu, rfl⟩
          rcases hx_j with ⟨v, _hv, hEq⟩
          exact hij ((Sigma.mk.inj hEq).1.symm)
        have hVset_union : (⋃ i ∈ Iset, Vset i) = A.verts := by
          ext x
          constructor
          · intro hx
            rcases (by simpa [Vset] using hx) with ⟨i, _hi, u, hu, rfl⟩
            simpa [Ai] using hu
          · intro hx
            have hxI : x.1 ∈ Iset := ⟨x, hx, rfl⟩
            have hxA : x.2 ∈ (Ai x.1).verts := by simpa [Ai] using hx
            -- Build the union membership witness `i = x.fst`.
            have hx' :
                ∃ i, i ∈ Iset ∧ ∃ u, u ∈ (Ai i).verts ∧ Sigma.mk i u = x :=
              ⟨x.1, hxI, x.2, hxA, rfl⟩
            simpa [Vset] using hx'

        have hCard' :
            (⋃ i ∈ Iset, Vset i).ncard = ∑ᶠ i ∈ Iset, (Vset i).ncard :=
          Set.Finite.ncard_biUnion hIset_finite hVset_finite hVset_disjoint
        have hVset_ncard : ∀ i : ι, (Vset i).ncard = (Ai i).verts.ncard := by
          intro i
          simpa [Vset] using
            (Set.ncard_image_of_injective (Ai i).verts (fun _ _ hab => eq_of_heq (Sigma.mk.inj hab).2))
        have hFinsum :
            (∑ᶠ i ∈ Iset, (Vset i).ncard) = ∑ i ∈ I, (Vset i).ncard :=
          finsum_mem_eq_finite_toFinset_sum (fun i => (Vset i).ncard) hIset_finite

        have hCard :
            A.verts.ncard = ∑ i ∈ I, (Ai i).verts.ncard := by
          calc
            A.verts.ncard = (⋃ i ∈ Iset, Vset i).ncard := by simpa [hVset_union]
            _ = ∑ i ∈ I, (Vset i).ncard := by simpa [hFinsum] using hCard'
            _ = ∑ i ∈ I, (Ai i).verts.ncard := by
              refine Finset.sum_congr rfl ?_
              intro i hi
              simpa [hVset_ncard i]

        simpa [hnA] using hCard.symm

      -- Sum bounds to get `|E| ≤ ε * n` in `ℝ`.
      have hSum_le :
          ((∑ i ∈ I, (Edel i).ncard : ℕ) : ℝ) ≤ ε * (n : ℝ) := by
        have hSum_le' :
            (∑ i ∈ I, ((Edel i).ncard : ℝ)) ≤
              ∑ i ∈ I, ε * ((Ai i).verts.ncard : ℝ) := by
          refine Finset.sum_le_sum ?_
          intro i hi
          simpa using hEdel_le i hi
        have hsumVerts :
            (∑ i ∈ I, ((Ai i).verts.ncard : ℝ)) = (n : ℝ) := by
          exact_mod_cast hVerts_sum
        calc
          ((∑ i ∈ I, (Edel i).ncard : ℕ) : ℝ) = ∑ i ∈ I, ((Edel i).ncard : ℝ) := by simp
          _ ≤ ∑ i ∈ I, ε * ((Ai i).verts.ncard : ℝ) := hSum_le'
          _ = ε * (∑ i ∈ I, ((Ai i).verts.ncard : ℝ)) := by
            simpa using (Finset.mul_sum (s := I) (f := fun i => ((Ai i).verts.ncard : ℝ)) ε).symm
          _ = ε * (n : ℝ) := by simpa [hsumVerts]

      have hE_real :
          (E.ncard : ℝ) ≤ ε * (n : ℝ) := by
        have hE_nat : E.ncard ≤ ∑ i ∈ I, (Edel i).ncard := hE_ncard_le_sum
        have : (E.ncard : ℝ) ≤ ((∑ i ∈ I, (Edel i).ncard : ℕ) : ℝ) := by
          exact_mod_cast hE_nat
        exact this.trans hSum_le

      -- `minEdgeDistToBipartite A` is at most `|E|`.
      have hMin_real :
          (SimpleGraph.minEdgeDistToBipartite A : ℝ) ≤ (E.ncard : ℝ) := by
        exact_mod_cast hMin_le_E

      exact hMin_real.trans hE_real

    -- Rewrite the maximum via `hEq` and conclude.
    simpa [hEq] using hA_bound
  · -- If there are no `n`-vertex subgraphs, the `sSup` is `0`.
    have hEmpty : S = ∅ := (Set.not_nonempty_iff_eq_empty).1 hS
    have : SimpleGraph.maxSubgraphEdgeDistToBipartite (SimpleGraph.sigma (G := G)) n = 0 := by
      simp [SimpleGraph.maxSubgraphEdgeDistToBipartite, S, hEmpty]
    -- `0 ≤ ε * n` since `ε ≥ 0`.
    simpa [this] using mul_nonneg hε (Nat.cast_nonneg n)

/-- The linear case of Erdős Problem 74 holds, assuming Rödl/Lovász's finite construction. -/
theorem erdos_74_linear_holds : erdos_74_linear.{u} := by
  intro ε hε
  classical
  -- Choose a Rödl/Lovász graph `G k` for each `k`.
  let Wk : ULift.{u} ℕ → Type u := fun k => Classical.choose (rodl_modified_kneser_exists ε hε k.down)
  let Gk : ∀ k : ULift.{u} ℕ, SimpleGraph (Wk k) :=
    fun k => Classical.choose (Classical.choose_spec (rodl_modified_kneser_exists ε hε k.down))
  have hχk : ∀ k : ULift.{u} ℕ, (k.down : ℕ∞) ≤ (Gk k).chromaticNumber := fun k =>
    (Classical.choose_spec (Classical.choose_spec (rodl_modified_kneser_exists ε hε k.down))).1
  have hbk :
      ∀ k : ULift.{u} ℕ,
        ∀ n : ℕ,
          (SimpleGraph.maxSubgraphEdgeDistToBipartite (Gk k) n : ℝ) ≤ ε * (n : ℝ) := fun k =>
    (Classical.choose_spec (Classical.choose_spec (rodl_modified_kneser_exists ε hε k.down))).2

  -- Disjoint union over `k`.
  let Ginf : SimpleGraph (Sigma Wk) := SimpleGraph.sigma (G := Gk)

  have hchi_inf : Ginf.chromaticNumber = ⊤ := by
    refine SimpleGraph.chromaticNumber_sigma_eq_top_of_unbounded (G := Gk) ?_
    intro n
    exact ⟨ULift.up (n + 1), by simpa using hχk (ULift.up (n + 1))⟩

  have hlin : ∀ n : ℕ, (SimpleGraph.maxSubgraphEdgeDistToBipartite Ginf n : ℝ) ≤ ε * (n : ℝ) := by
    intro n
    simpa [Ginf] using
      SimpleGraph.maxSubgraphEdgeDistToBipartite_sigma_le_linear (G := Gk) (ε := ε) (hε := le_of_lt hε) hbk n

  refine ⟨(Sigma Wk : Type u), Ginf, hchi_inf, fun n => ?_⟩
  exact (hlin n)

/-!
## Relations between variants
-/

/-- `Nat.sqrt n → ∞`, so the `√n`-variant is a special case of the main conjecture. -/
theorem tendsto_nat_sqrt_atTop : Tendsto Nat.sqrt atTop atTop := by
  rw [tendsto_atTop_atTop]
  intro b
  refine ⟨b * b, ?_⟩
  intro a ha
  exact (Nat.le_sqrt).2 ha

theorem erdos_74_sqrt_of_erdos_74 : erdos_74.{u} → erdos_74_sqrt.{u} := by
  intro h
  have hs : Tendsto Nat.sqrt atTop atTop := tendsto_nat_sqrt_atTop
  rcases h Nat.sqrt hs with ⟨W, G, hχ, hbound⟩
  exact ⟨W, G, hχ, hbound⟩

/-!
## Research Notes

### Known Results (from erdosproblems.com):
- Rödl (1982): Such a graph exists when f(n) = εn for any fixed ε > 0
- The case f(n) = √n remains open
- The statement FAILS for graphs with chromatic number ℵ₁

### Formalization caveat (Mathlib):
`SimpleGraph.chromaticNumber` in Mathlib is `ℕ∞`, so it only distinguishes *finite* vs *infinite*,
and cannot express the fine distinction between `χ(G) = ℵ₀` and `χ(G) = ℵ₁`. Formalizing the
`ℵ₁` negative result would require a cardinal-valued chromatic number.

### Related Work:
- Lambie-Hanson (arXiv:1902.08177): Solved the CHROMATIC GROWTH question
  (different from edge-deletion to bipartite)
- EHS82: Original paper defining maxSubgraphEdgeDistToBipartite
  - In EHS82 notation this is `f_W^{(3)}(n)` (Section 3, “Omitting edges of a subgraph”)
  - EHS82 also explicitly asks whether `f_W^{(3)}(n)` can grow “very slowly” for χ(G)=ω
    (their Problem 3), which matches the modern Erdős Problems phrasing.

### Key Insight:
The edge-deletion formulation is STRONGER than chromatic growth.
Making bipartite means χ ≤ 2, not just slowly growing χ.
-/

end Erdos.Problem074
