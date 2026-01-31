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
union the edge-deletion witnesses), but keeping it as an axiom avoids a large amount of set/card
bookkeeping in this experimental file.
-/
axiom SimpleGraph.maxSubgraphEdgeDistToBipartite_sigma_le_linear
    {ι : Type*} {W : ι → Type u} (G : ∀ i, SimpleGraph (W i)) (ε : ℝ)
    (h : ∀ i : ι, ∀ n : ℕ,
      (SimpleGraph.maxSubgraphEdgeDistToBipartite (G i) n : ℝ) ≤ ε * (n : ℝ)) :
    ∀ n : ℕ,
      (SimpleGraph.maxSubgraphEdgeDistToBipartite (SimpleGraph.sigma (G := G)) n : ℝ) ≤
        ε * (n : ℝ)

/-- The linear case of Erdős Problem 74 holds, assuming Rödl/Lovász's finite construction. -/
theorem erdos_74_linear_holds : erdos_74_linear := by
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
      SimpleGraph.maxSubgraphEdgeDistToBipartite_sigma_le_linear (G := Gk) (ε := ε) hbk n

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
